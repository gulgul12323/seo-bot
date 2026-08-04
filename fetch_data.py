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
    """텍스트 내 금액 수치를 파싱하여 가중치 점수를 산출합니다."""
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

def is_valid_policy_news(title, pub_dt):
    """
    [강력한 2중 필터]
    1. 단순 행사/동향/간담회 기사 100% 제거
    2. 실제 모집/신청/지급 기사만 통과
    """
    # 🚫 [무조건 제외] 단순 지자체 행사, 간담회, 협약 기사
    junk_keywords = [
        "간담회", "출범", "네트워크", "포럼", "협약", "MOU", "원테이블", 
        "특강", "토론회", "청년의 날", "체결", "마감", "종료", "선발 완료", "접수 마감"
    ]
    if any(kw in title for kw in junk_keywords):
        return False

    # ✅ [필수 포함] 실제 혜택/모집 관련 키워드가 하나라도 있어야 함
    valid_keywords = ["모집", "신청", "지원", "수당", "선발", "지급", "접수", "달성", "혜택", "통장", "월세"]
    if not any(kw in title for kw in valid_keywords):
        return False

    # 날짜 검증 (60일 초과 구형 기사 차단)
    if pub_dt:
        now = datetime.now(timezone.utc)
        if (now - pub_dt).days > 60:
            return False

    return True

def calculate_priority_score(title, pub_dt):
    """금액 규모 + 최신성 가중치 계산"""
    money_score = extract_monetary_value(title)
    recency_score = 0
    if pub_dt:
        now = datetime.now(timezone.utc)
        hours_ago = max(0, (now - pub_dt).total_seconds() / 3600)
        recency_score = max(0, 100 - (hours_ago / 2))

    return (money_score * 0.6) + (recency_score * 0.4)

def fetch_rss_from_url(url):
    """RSS URL 안전 수집 함수"""
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
    타겟팅된 정밀 키워드로 실시간 RSS를 수집합니다.
    """
    # 단순 '청년정책'을 빼고 실제 혜택 중심 키워드로 검색
    search_query = "청년 지원금 OR 청년수당 OR 청년 월세 지원 OR 청년 모집"
    rss_urls = [
        f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query)}&hl=ko&gl=KR&ceid=KR:ko",
        "https://www.korea.kr/rss/policy.xml"
    ]

    for url in rss_urls:
        try:
            print(f"📡 정밀 타겟팅 RSS 수집 시도 중: {url[:50]}...")
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

                # ✋ 2중 정밀 필터링 적용 (간담회/출범 기사 싹 걸러냄)
                if not is_valid_policy_news(clean_title, pub_dt):
                    continue

                p_score = calculate_priority_score(clean_title, pub_dt)

                candidate = {
                    "title": clean_title,
                    "target": "해당 지자체 및 정부 지원 자격 요건 충족 청년",
                    "amount": "공식 공고문 참조 (상세 지원 규모 확인)",
                    "deadline": "공고문 지정 모집 및 접수 기간",
                    "apply_path": link if link else "공식 신청 사이트 및 지자체 포털",
                    "secret_tip": f"보도 시각: {pub_date_str[:16] if pub_date_str else '최신'} | 공식 공고문 수혜 조건 확인 필수.",
                    "priority_score": p_score
                }
                candidates.append(candidate)

            if candidates:
                # 가중치 순 정렬 후 상위 추출
                candidates.sort(key=lambda x: x["priority_score"], reverse=True)
                
                for c in candidates:
                    c.pop("priority_score", None)

                print(f"✅ 정밀 검증 성공! 실제 지원금 공고 기사만 {len(candidates)}개 선별되었습니다.")
                return candidates

        except Exception as e:
            print(f"⚠️ RSS 수집 실패 ({url[:30]}...): {e}")

    return None

def get_subsidy_data():
    """
    실시간 RSS (정밀 필터) ➔ 실패 시 youth_db.json
    """
    past_text = get_already_posted_text()

    # 1. 정밀 RSS 수집
    news_items = fetch_rss_news()

    if news_items:
        unposted = [s for s in news_items if s["title"] not in past_text]

        if unposted:
            selected_count = min(3, len(unposted))
            selected = unposted[:selected_count]
            print(f"✨ [정밀 RSS] 가짜 뉴스 배제된 진짜 지원금 공고 {selected_count}개 선택 완료!")
            return {
                "scope_type": "national",
                "region_name": "최신 알짜 청년 지원금 & 모집 공고 소식",
                "subsidies": selected
            }

    # 2. RSS 예외 시 youth_db.json 스캔
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

    # 3. 비상 백업 DB
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
