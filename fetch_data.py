import os
import json
import random
import urllib.request
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime

def get_already_posted_keywords():
    """
    실제로 블로그에 발행된 모든 글(posts.json 및 posts/*.md)을 스캔하여
    이미 작성된 텍스트 전체를 하나의 문자열로 모아 반환합니다. (100% 중복 방지)
    """
    posted_text = ""

    # 1. posts.json 스캔
    if os.path.exists("posts.json"):
        try:
            with open("posts.json", "r", encoding="utf-8") as f:
                posts_data = json.load(f)
                for post in posts_data:
                    posted_text += post.get("content", "") + "\n"
        except Exception as e:
            print(f"⚠️ posts.json 읽기 예외: {e}")

    # 2. posts/ 폴더 내 마크다운 파일 스캔
    if os.path.exists("posts"):
        try:
            for fname in os.listdir("posts"):
                if fname.endswith(".md"):
                    fpath = os.path.join("posts", fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        posted_text += f.read() + "\n"
        except Exception as e:
            print(f"⚠️ posts 폴더 스캔 예외: {e}")

    return posted_text

def is_subsidy_valid(subsidy):
    """
    오늘 날짜 및 현재 월/시즌 기준으로 지원금이 유효한지 2중 검증하는 함수
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_month = now.month

    deadline = str(subsidy.get("deadline", ""))
    end_date = str(subsidy.get("end_date", ""))

    # 하반기(7월 이후) 기준 지나간 분기/시즌 차단
    if current_month >= 7:
        past_keywords = ["상반기", "1분기", "2분기", "매년 초", "1월", "2월", "3월", "4월", "5월", "6월"]
        if any(k in deadline for k in past_keywords):
            if not any(k in deadline for k in ["하반기", "상시", "연중", "소진", "9월", "11월"]):
                return False

    # end_date 일자 직접 비교
    if end_date and any(char.isdigit() for char in end_date):
        if not any(k in end_date for k in ["상시", "연중", "소진", "매월", "분기"]):
            try:
                if str(end_date) < today_str:
                    return False
            except Exception:
                pass

    if any(k in deadline for k in ["접수 마감", "모집 종료", "선발 완료"]):
        if "소진 시" not in deadline and "상시" not in deadline:
            return False

    return True

def fetch_from_youth_center_api():
    """
    Vercel 중계 API(https://www.youthzip.com/api/youth)를 호출하여
    해외 IP 차단(Timeout) 없이 온통청년 데이터를 실시간 수집합니다.
    """
    # www 및 비-www 도메인 호환 처리
    target_urls = [
        "https://www.youthzip.com/api/youth",
        "https://youthzip.com/api/youth"
    ]

    context = ssl._create_unverified_context()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/xml, text/xml, */*'
    }

    xml_data = None
    for url in target_urls:
        try:
            print(f"📡 Vercel 중계 API 호출 중: {url}")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12, context=context) as response:
                xml_data = response.read().decode('utf-8')
                if "<emp>" in xml_data:
                    break
        except Exception as e:
            print(f"⚠️ {url} 호출 실패: {e}")

    if not xml_data or "<emp>" not in xml_data:
        print("💡 Vercel 중계 API 응답 없음. 비상 내장 DB로 자동 전환합니다.")
        return None

    try:
        root = ET.fromstring(xml_data)
        emp_list = root.findall('.//emp')

        if not emp_list:
            print("⚠️ API XML 데이터는 있으나 <emp> 태그가 0개입니다.")
            return None

        subsidies = []
        for emp in emp_list:
            title = emp.findtext('polyBizSjnm', '').strip()
            summary = emp.findtext('polyItcnCn', '').strip()
            target = emp.findtext('ageInfo', '만 19세~39세 청년').strip()
            amount = emp.findtext('sporCn', '지자체 공고 참조').strip()
            deadline = emp.findtext('rqutPrdCn', '상시/지정기간').strip()
            apply_path = emp.findtext('rqutUrla', '').strip()
            cnd_info = emp.findtext('cndPrdCn', '').strip()

            if not apply_path:
                apply_path = emp.findtext('rfcSiteUrla1', '온통청년 포털 및 지자체 홈페이지').strip()

            if not title:
                continue

            clean_amount = amount.replace('\n', ' ') if amount else "지자체 공고문 참조"
            if len(clean_amount) > 80:
                clean_amount = clean_amount[:78] + "..."

            clean_target = target.replace('\n', ' ') if target else "청년 가구 및 구직자"
            if len(clean_target) > 80:
                clean_target = clean_target[:78] + "..."

            secret_tip = cnd_info if cnd_info else summary
            if len(secret_tip) > 100:
                secret_tip = secret_tip[:98] + "..."

            item = {
                "title": title,
                "target": clean_target,
                "amount": clean_amount,
                "deadline": deadline if deadline else "상시 접수",
                "end_date": "상시",
                "apply_path": apply_path if apply_path else "온통청년 포털 온라인 접수",
                "secret_tip": secret_tip if secret_tip else "자세한 자격조건은 공식 공고문 확인 필수."
            }

            if is_subsidy_valid(item):
                subsidies.append(item)

        print(f"✅ [API 성공] Vercel 중계로 온통청년 실시간 데이터 {len(subsidies)}개 수집 성공!")
        return subsidies

    except Exception as e:
        print(f"⚠️ XML 파싱 예외 발생: {e}")
        return None

def get_subsidy_data():
    """
    Vercel 중계 API 우선 활용 ➔ 실패 시 내장 DB 사용.
    과거 블로그 포스팅 전체 스캔으로 100% 중복을 방지합니다.
    """
    # 1. 이미 블로그에 올렸던 글의 모든 텍스트 수집
    past_text = get_already_posted_keywords()

    # 2. [우선순위 1] Vercel 중계 API 통해 온통청년 데이터 수집
    api_subsidies = fetch_from_youth_center_api()
    if api_subsidies:
        # 블로그에 한 번도 제목이 등장하지 않은 신규 지원금 추출
        unposted_api = [s for s in api_subsidies if s["title"] not in past_text]

        if unposted_api:
            selected_count = min(3, len(unposted_api))
            selected_subsidies = random.sample(unposted_api, selected_count)
            print(f"✨ [온통청년 API] 미발행 신규 지원금 {selected_count}개 선택 완료!")
            return {
                "scope_type": "national",
                "region_name": "전국/지자체",
                "subsidies": selected_subsidies
            }
        else:
            selected_count = min(3, len(api_subsidies))
            selected_subsidies = random.sample(api_subsidies, selected_count)
            print("🔄 [온통청년 API] 모든 수집 항목이 작성되어 재순환 선택했습니다.")
            return {
                "scope_type": "national",
                "region_name": "전국/지자체",
                "subsidies": selected_subsidies
            }

    # 3. [우선순위 2] 비상 내장 DB (전국 광역/기초 지자체)
    print("💡 내장 고품질 DB에서 중복 없는 신규 지원금을 선택합니다.")
    data_pool = [
        # [서울특별시]
        {
            "scope_type": "local",
            "region_name": "서울특별시",
            "subsidies": [
                {
                    "title": "2026 서울시 청년수당 (월 50만 원 지원)",
                    "target": "서울 거주 만 19세~34세 미취업 청년 (중위소득 150% 이하)",
                    "amount": "월 50만 원씩 최대 6개월 (총 300만 원 지급)",
                    "deadline": "상반기/하반기 지정 모집 기간",
                    "end_date": "상시",
                    "apply_path": "청년몽땅정보통 온라인 신청",
                    "secret_tip": "주 30시간 이하 단기 알바생도 신청 가능하며 구직활동 보고서 제출 필수."
                },
                {
                    "title": "서울 청년 대중교통비 지원 사업",
                    "target": "서울 거주 만 19세~24세 청년",
                    "amount": "연 최대 10만 원 교통비 마일리지 환급",
                    "deadline": "상시/지정 모집 기간",
                    "end_date": "상시",
                    "apply_path": "청년몽땅정보통 홈페이지",
                    "secret_tip": "기후동행카드 및 기존 교통카드 이용 내역으로 연 1회 일괄 환급 혜택."
                }
            ]
        },
        # [부산광역시]
        {
            "scope_type": "local",
            "region_name": "부산광역시",
            "subsidies": [
                {
                    "title": "부산 청년 월세 파격 지원 사업",
                    "target": "부산 거주 무주택 청년 가구주 (임차보증금 1억 원 이하)",
                    "amount": "월 최대 20만 원 (연 최대 240만 원 환급)",
                    "deadline": "상시 접수 (예산 소진 시 마감)",
                    "end_date": "상시",
                    "apply_path": "부산청년플랫폼 온라인 접수",
                    "secret_tip": "국토부 청년월세 특별지원과 중복은 안 되지만 소득 기준이 더 완화됨."
                },
                {
                    "title": "2026 부산 청년 끌어안음 주택임차보증금 이자지원",
                    "target": "부산 거주 만 19세~39세 무주택 청년",
                    "amount": "대출 연 2.0% 이자 지원 (연 최대 200만 원 절감)",
                    "deadline": "연중 상시 접수",
                    "end_date": "상시",
                    "apply_path": "부산청년플랫폼 및 부산은행 앱",
                    "secret_tip": "부산 시내 자취방 구할 때 은행 전월세 대출 이자 부담을 대폭 낮춰줌."
                }
            ]
        },
        # [경기도]
        {
            "scope_type": "local",
            "region_name": "경기도",
            "subsidies": [
                {
                    "title": "2026 경기도 청년 기본소득 (하반기 분기별 지급)",
                    "target": "경기도에 3년 이상 연속 거주 중인 만 24세 청년",
                    "amount": "분기별 25만 원 (연 총 100만 원, 지역화폐 지급)",
                    "deadline": "하반기 3분기(9월), 4분기(11월) 접수",
                    "end_date": "2026-11-30",
                    "apply_path": "경기도 잡아바 어플라이(apply.jobaba.net)",
                    "secret_tip": "소득/재산/취업 여부 전혀 안 봄! 만 24세 나이 조건만 맞으면 100% 지급."
                },
                {
                    "title": "경기도 청년 면접수당 (역대 최대 규모)",
                    "target": "경기도 거주 만 18세~39세 구직 청년",
                    "amount": "면접 1회당 5만 원 (연 최대 10회, 총 50만 원 지역화폐)",
                    "deadline": "하반기 지정 접수 기간",
                    "end_date": "2026-12-31",
                    "apply_path": "잡아바 어플라이 온라인 신청",
                    "secret_tip": "이직 준비 중인 단기 알바생, 지방 소재 기업 면접 본 경기도 청년도 증빙 시 100% 지급."
                }
            ]
        },
        # [충청도 / 대전]
        {
            "scope_type": "local",
            "region_name": "충청도·대전",
            "subsidies": [
                {
                    "title": "2026 대전 청년 주택임차보증금 이자지원",
                    "target": "대전 거주 또는 이전 예정인 만 19세~39세 무주택 청년",
                    "amount": "대출한도 7,000만 원 이내 연 3.5% 이자 지원 (연 최대 245만 원 절감)",
                    "deadline": "연중 상시 접수",
                    "end_date": "상시",
                    "apply_path": "대전 청년포털 '청년틈새' 온라인 신청",
                    "secret_tip": "대전 시내 대학가 주변 자취방 구할 때 은행 대출이자 부담을 거의 0원으로 만듦."
                }
            ]
        },
        # [전국 공통]
        {
            "scope_type": "national",
            "region_name": "전국 공통",
            "subsidies": [
                {
                    "title": "2026 청년도약계좌 (정부 기여금+비과세 혜택)",
                    "target": "만 19세~34세 일하는 청년 (개인소득 7,500만 원 이하)",
                    "amount": "5년 만기 시 최대 5,000만 원 목돈 마련 (정부지원금+비과세)",
                    "deadline": "매월 초 가입 신청 기간",
                    "end_date": "상시",
                    "apply_path": "주요 은행 모바일 앱",
                    "secret_tip": "육아휴직자, 육아수당 수령자도 가입 가능하며 나이 산정 시 군복무 기간 차감."
                },
                {
                    "title": "2026 K-Digital Training (KDT) IT/AI 교육비 전액 지원",
                    "target": "구직자(대학생, 취준생, 이직희망자)",
                    "amount": "수강료 100% 전액 국비지원 + 월 최대 31만 6천 원 훈련수당 지급",
                    "deadline": "상시 과정 개설",
                    "end_date": "상시",
                    "apply_path": "HRD-Flex 및 고용24 홈페이지",
                    "secret_tip": "전공 상관없이 문과생도 신청 가능하며 출석률 80% 이상 시 수당 지급."
                }
            ]
        }
    ]

    # 내장 DB 중 과거 포스팅에 제목이 단 한 번도 나오지 않은 그룹 필터링
    unposted_groups = []
    for group in data_pool:
        fresh_subsidies = [s for s in group["subsidies"] if s["title"] not in past_text]
        if fresh_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = fresh_subsidies
            unposted_groups.append(group_copy)

    if unposted_groups:
        selected_data = random.choice(unposted_groups)
        print(f"✨ [신규 지원금 추출] [{selected_data['region_name']}] 지원금이 선택되었습니다.")
        return selected_data

    print("🔄 [순환 선택] 모든 DB 지원글이 작성되어 순환 선택합니다.")
    return random.choice(data_pool)

# 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
