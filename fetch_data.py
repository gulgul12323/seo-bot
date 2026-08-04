import os
import json
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def get_already_posted_text():
    """블로그에 이미 작성된 모든 글(posts.json 및 posts/*.md)을 스캔하여 중복 방지 텍스트를 수집합니다."""
    posted_text = ""
    if os.path.exists("posts.json"):
        try:
            with open("posts.json", "r", encoding="utf-8") as f:
                posts_data = json.load(f)
                for post in posts_data:
                    posted_text += post.get("title", "") + " " + post.get("content", "") + "\n"
        except Exception as e:
            print(f"⚠️ posts.json 읽기 예외: {e}")

    if os.path.exists("posts"):
        try:
            for fname in os.listdir("posts"):
                if fname.endswith(".md"):
                    with open(os.path.join("posts", fname), "r", encoding="utf-8") as f:
                        posted_text += f.read() + "\n"
        except Exception as e:
            print(f"⚠️ posts 폴더 스캔 예외: {e}")

    return posted_text

def extract_monetary_value(text):
    """
    텍스트 내 금액 수치(억 원, 만 원, 월 XX만 원)를 파싱하여 금액 가중치 점수를 환산합니다.
    """
    score = 0
    # '억' 단위 수치 추출 (예: 1억 = 10,000점)
    eok_matches = re.findall(r'(\d+(?:\.\d+)?)\s*억', text)
    for m in eok_matches:
        score += float(m) * 10000

    # '만원' 단위 수치 추출 (예: 300만원 = 300점)
    man_matches = re.findall(r'(\d+(?:\.\d+)?)\s*만\s*원', text)
    for m in man_matches:
        score += float(m)

    # '월 XX만원' 매칭 시 연간 가치 감안 가속 가중치 (예: 월 50만 -> 300점)
    month_matches = re.findall(r'월\s*(\d+(?:\.\d+)?)\s*만', text)
    for m in month_matches:
        score += float(m) * 6

    return score

def is_valid_policy(title, pub_dt):
    """
    기한 엄수 및 유효성 검증 함수:
    이미 마감되었거나 60일 이상 지난 오래된 정보는 제외합니다.
    """
    # 1. 마감/종료 관련 키워드가 제목에 들어간 경우 즉시 제외
    expired_keywords = ["마감", "종료", "선발 완료", "접수 마감", "모집 완료", "완료"]
    if any(kw in title for kw in expired_keywords):
        return False

    # 2. 발행일 기준 60일 초과된 구형 소식 제외
    if pub_dt:
        now = datetime.now(timezone.utc)
        days_diff = (now - pub_dt).days
        if days_diff > 60:
            return False

    return True

def calculate_priority_score(item):
    """
    지원금 절댓값 규모(60%) + 소식의 최신성(40%)을 결합한 가중치 종합 점수를 계산합니다.
    """
    title = item["title"]
    pub_dt = item["pub_dt"]

    # 1. 지원금액 규모 가중치
    money_score = extract_monetary_value(title)

    # 2. 최신성 가중치 (최근 보도일수록 높은 점수)
    recency_score = 0
    if pub_dt:
        now = datetime.now(timezone.utc)
        hours_ago = max(0, (now - pub_dt).total_seconds() / 3600)
        recency_score = max(0, 100 - (hours_ago / 2))  # 24시간 이내 최상위, 시간 지날수록 점수 감점

    # 종합 가중치 점수 합산 (금액 반영비율 60% + 최신성 반영비율 40%)
    total_score = (money_score * 0.6) + (recency_score * 0.4)
    return total_score

def fetch_rss_news():
    """
    구글 뉴스 RSS에서 '청년 지원금/수당/정책' 최신 뉴스를 수집하고 가중치순으로 정렬합니다.
    """
    query = "청년 지원금 OR 청년수당 OR 청년정책 지원"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read().decode('utf-8')

        root = ET.fromstring(xml_data)
        items = root.findall('.//item')

        candidates = []
        for item in items:
            raw_title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pub_date_str = item.findtext('pubDate', '').strip()

            if not raw_title:
                continue

            # 제목 정제 (언론사명 분리)
            clean_title = raw_title.split(' - ')[0] if ' - ' in raw_title else raw_title

            # 작성 날짜 파싱
            pub_dt = None
            if pub_date_str:
                try:
                    pub_dt = parsedate_to_datetime(pub_date_str)
                except Exception:
                    pass

            # [엄격 검증] 기한 만료 및 유효성 확인
            if not is_valid_policy(clean_title, pub_dt):
                continue

            candidate = {
                "title": clean_title,
                "target": "해당 지자체 및 정부 지원 정책 대상 청년",
                "amount": "최신 공식 공고문 및 보도자료 지원 규모 참조",
                "deadline": "상시 / 지정 모집 기간 (공식 공고 확인 필수)",
                "apply_path": link if link else "공식 신청 사이트 및 지자체 포털",
                "secret_tip": "최신 공식 보도 소식입니다. 지원 자격 및 세부 일정은 공식 공고문 확인이 필요합니다.",
                "pub_dt": pub_dt
            }

            # [가중치 산출] 금액 크기 + 최신성 가중치 점수 합산
            candidate["priority_score"] = calculate_priority_score(candidate)
            candidates.append(candidate)

        # 가중치 점수가 높은 순(내림차순)으로 최고 우선순위 항목 정렬
        candidates.sort(key=lambda x: x["priority_score"], reverse=True)
        return candidates

    except Exception as e:
        print(f"⚠️ RSS 수집 중 예외 발생: {e}")
        return None

def get_subsidy_data():
    """
    1순위: 기한 및 가중치(최신성+지원금액) 검증을 거친 실시간 RSS 소식 선택
    2순위: 수집 예외 발생 시 비상 백업 DB 활용
    """
    past_text = get_already_posted_text()

    print("📡 최신성 및 지원금액 가중치 반영 실시간 RSS 데이터 수집 중...")
    news_items = fetch_rss_news()

    if news_items:
        # 이미 발행된 포스팅 제외
        unposted = [s for s in news_items if s["title"] not in past_text]

        if unposted:
            # 가중치 점수가 가장 높은 상위 3개 선정
            selected_count = min(3, len(unposted))
            selected = unposted[:selected_count]
            print(f"✨ [우선순위 가중치 알고리즘] 가장 혜택이 크고 최신인 지원금 {selected_count}개 선택 완료!")
            return {
                "scope_type": "national",
                "region_name": "최신 고혜택 청년 지원 정책 소식",
                "subsidies": selected
            }
        else:
            selected_count = min(3, len(news_items))
            selected = news_items[:selected_count]
            print("🔄 [실시간 RSS] 모든 뉴스가 이미 작성되어 순환 선택했습니다.")
            return {
                "scope_type": "national",
                "region_name": "최신 고혜택 청년 지원 정책 소식",
                "subsidies": selected
            }

    # 2. RSS 통신 예외 시 비상 백업 DB
    print("💡 RSS 통신 예외 발생으로 백업 DB를 선택합니다.")
    backup_pool = [
        {
            "title": "2026 청년도약계좌 (정부 기여금+비과세 혜택)",
            "target": "만 19세~34세 일하는 청년",
            "amount": "5년 만기 시 최대 5,000만 원 목돈 마련",
            "deadline": "매월 초 가입 신청 기간",
            "apply_path": "주요 은행 모바일 앱",
            "secret_tip": "정부 기여금 및 비과세 혜택 제공."
        },
        {
            "title": "2026 K-Digital Training IT/AI 교육비 전액 지원",
            "target": "구직자(대학생, 취준생, 이직희망자)",
            "amount": "수강료 100% 전액 국비지원 + 월 훈련수당",
            "deadline": "상시 과정 개설",
            "apply_path": "고용24 홈페이지",
            "secret_tip": "전공 상관없이 문과생도 신청 가능."
        }
    ]

    return {
        "scope_type": "national",
        "region_name": "전국 주요 청년 지원 정책",
        "subsidies": backup_pool
    }

# 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
