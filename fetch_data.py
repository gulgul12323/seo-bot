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
    """텍스트 내 금액 수치(억 원, 만 원, 월 XX만 원)를 파싱하여 금액 가중치 점수를 환산합니다."""
    score = 0
    eok_matches = re.findall(r'(\d+(?:\.\d+)?)\s*억', text)
    for m in eok_matches:
        score += float(m) * 10000

    man_matches = re.findall(r'(\d+(?:\.\d+)?)\s*만\s*원', text)
    for m in man_matches:
        score += float(m)

    month_matches = re.findall(r'월\s*(\d+(?:\.\d+)?)\s*만', text)
    for m in month_matches:
        score += float(m) * 6

    return score

def is_valid_policy(title, pub_dt):
    """기한 만료 및 이미 마감된 소식 제외"""
    expired_keywords = ["마감", "종료", "선발 완료", "접수 마감", "모집 완료", "완료"]
    if any(kw in title for kw in expired_keywords):
        return False

    if pub_dt:
        now = datetime.now(timezone.utc)
        days_diff = (now - pub_dt).days
        if days_diff > 60:
            return False

    return True

def calculate_priority_score(item):
    """금액 규모(60%) + 최신성(40%) 가중치 계산"""
    title = item["title"]
    pub_dt = item["pub_dt"]

    money_score = extract_monetary_value(title)
    recency_score = 0
    if pub_dt:
        now = datetime.now(timezone.utc)
        hours_ago = max(0, (now - pub_dt).total_seconds() / 3600)
        recency_score = max(0, 100 - (hours_ago / 2))

    return (money_score * 0.6) + (recency_score * 0.4)

def fetch_rss_from_url(url):
    """RSS URL을 안전하게 수집하는 공통 함수 (503 차단 방지 헤더 적용)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        return response.read().decode('utf-8')

def fetch_rss_news():
    """
    1차: 구글 뉴스 RSS
    2차: 대한민국 정책브리핑 RSS (구글 503 에러 시 자동 백업 우회)
    """
    rss_urls = [
        # 1차: 구글 뉴스 RSS
        f"https://news.google.com/rss/search?q={urllib.parse.quote('청년 지원금 OR 청년수당 OR 청년정책')}&hl=ko&gl=KR&ceid=KR:ko",
        # 2차: 대한민국 정책브리핑 (정부 공식 RSS)
        "https://www.korea.kr/rss/policy.xml"
    ]

    for url in rss_urls:
        try:
            print(f"📡 RSS 수집 시도 중: {url[:50]}...")
            xml_data = fetch_rss_from_url(url)
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')

            candidates = []
            for item in items:
                raw_title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                pub_date_str = item.findtext('pubDate', '').strip()

                if not raw_title:
                    continue

                clean_title = raw_title.split(' - ')[0] if ' - ' in raw_title else raw_title

                pub_dt = None
                if pub_date_str:
                    try:
                        pub_dt = parsedate_to_datetime(pub_date_str)
                    except Exception:
                        pass

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

                candidate["priority_score"] = calculate_priority_score(candidate)
                candidates.append(candidate)

            if candidates:
                candidates.sort(key=lambda x: x["priority_score"], reverse=True)
                print(f"✅ RSS 수집 성공! ({len(candidates)}개 수집됨)")
                return candidates

        except Exception as e:
            print(f"⚠️ RSS 수집 실패 ({url[:30]}...): {e}")

    return None

def get_subsidy_data():
    """
    실시간 RSS ➔ 실패 시 youth_db.json ➔ 중복 엄격 필터링
    """
    past_text = get_already_posted_text()

    # 1. 실시간 RSS 수집
    news_items = fetch_rss_news()

    if news_items:
        # 이미 블로그에 올렸던 제목은 엄격하게 제거
        unposted = [s for s in news_items if s["title"] not in past_text]

        if unposted:
            selected_count = min(3, len(unposted))
            selected = unposted[:selected_count]
            print(f"✨ [우선순위 RSS] 중복 없는 신규 지원금 {selected_count}개 선택 완료!")
            return {
                "scope_type": "national",
                "region_name": "최신 고혜택 청년 지원 정책 소식",
                "subsidies": selected
            }

    # 2. RSS 실패 또는 모두 중복일 경우 youth_db.json 스캔
    print("💡 youth_db.json 파일에서 중복 없는 신규 데이터를 찾습니다.")
    db_file = "youth_db.json"
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                db_pool = json.load(f)

            unposted_db = [s for s in db_pool if s.get("title") and s.get("title") not in past_text]
            if unposted_db:
                selected_count = min(3, len(unposted_db))
                selected = random.sample(unposted_db, selected_count)
                print(f"✨ [youth_db.json] 중복 없는 신규 지원금 {selected_count}개 선택 완료!")
                return {
                    "scope_type": "national",
                    "region_name": "전국 주요 청년 지원 정책",
                    "subsidies": selected
                }
        except Exception as e:
            print(f"⚠️ youth_db.json 읽기 예외: {e}")

    # 3. 비상 백업 DB (중복 체크 필수 적용)
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
        },
        {
            "title": "2026 청년월세 특별지원 (월 최대 20만 원)",
            "target": "만 19세~34세 무주택 청년",
            "amount": "월 최대 20만 원씩 12개월(최대 240만 원) 지원",
            "deadline": "연중 상시 접수",
            "apply_path": "복지로 홈페이지 또는 주민센터",
            "secret_tip": "청년 독립 가구 소득 기준 확인 필수."
        }
    ]

    unposted_backup = [s for s in backup_pool if s["title"] not in past_text]
    if unposted_backup:
        selected = random.sample(unposted_backup, min(3, len(unposted_backup)))
    else:
        selected = random.sample(backup_pool, min(3, len(backup_pool)))

    return {
        "scope_type": "national",
        "region_name": "전국 주요 청년 지원 정책",
        "subsidies": selected
    }

fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
