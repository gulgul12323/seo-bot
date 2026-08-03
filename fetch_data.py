import os
import json
import random
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

def is_subsidy_valid(subsidy):
    """
    오늘 날짜 및 현재 월/시즌 기준으로 지원금이 유효한지 2중 검증하는 함수
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_month = now.month

    deadline = str(subsidy.get("deadline", ""))
    end_date = str(subsidy.get("end_date", ""))

    # 1. 하반기(7월 이후) 기준 이미 지나간 시즌(상반기, 연초, 1~2분기) 키워드 즉시 차단
    if current_month >= 7:
        past_keywords = ["상반기", "1분기", "2분기", "매년 초", "1월", "2월", "3월", "4월", "5월", "6월"]
        if any(k in deadline for k in past_keywords):
            if not any(k in deadline for k in ["하반기", "상시", "연중", "소진", "9월", "11월"]):
                return False

    # 2. end_date(마감일자 YYYY-MM-DD) 명시 시 날짜 직접 비교
    if end_date and any(char.isdigit() for char in end_date):
        if not any(k in end_date for k in ["상시", "연중", "소진", "매월", "분기"]):
            try:
                if str(end_date) < today_str:
                    return False
            except Exception:
                pass

    # 3. deadline 마감 표기 검증
    if any(k in deadline for k in ["접수 마감", "모집 종료", "선발 완료"]):
        if "소진 시" not in deadline and "상시" not in deadline:
            return False

    return True

def fetch_from_youth_center_api():
    """
    온통청년(청년센터) 오픈 API를 호출하여 실시간 청년 정책 데이터를 수집합니다.
    """
    api_key = os.environ.get("YOUTH_CENTER_API_KEY", "").strip()
    if not api_key:
        print("⚠️ [API 필독] YOUTH_CENTER_API_KEY 가 깃허브 Secrets에 설정되지 않았습니다.")
        return None

    url = f"https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey={api_key}&pageIndex=1&display=50"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read().decode('utf-8')

        # API 에러 응답 분기 처리
        if "<resultCode>" in xml_data or "<errMsg>" in xml_data or "openApiVkey" in xml_data and "ERROR" in xml_data:
            print(f"⚠️ [API 에러] 온통청년 API키가 승인 대기 중이거나 유효하지 않습니다: {xml_data[:200]}")
            return None

        root = ET.fromstring(xml_data)
        emp_list = root.findall('.//emp')

        if not emp_list:
            print(f"⚠️ [API 경고] 온통청년 API 응답 데이터(emp)가 0개입니다. 응답 내용: {xml_data[:200]}")
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

        print(f"✅ [API 성공] 온통청년 API 수집 완료: 총 {len(subsidies)}개 최신 정책 수집됨.")
        return subsidies

    except Exception as e:
        print(f"⚠️ [API 예외] 온통청년 API 통신 중 오류 발생: {e}")
        return None

def get_subsidy_data():
    """
    과거 발행된 모든 포스팅 본문을 100% 검사하여 중복을 차단하고,
    온통청년 API 데이터를 우선 활용하여 추출합니다.
    """
    data_pool = [
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
                    "secret_tip": "국토부 청년월세 특별지원과 중복은 안 되지만, 소득 기준이 더 완화되어 국토부 탈락자가 신청하기 최적."
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
                    "secret_tip": "소득/재산/취업 여부 전혀 안 봄! 만 24세 나이 조건만 맞으면 100% 지급하는 경기 청년 전용 돈."
                },
                {
                    "title": "경기도 청년 면접수당 (역대 최대 규모)",
                    "target": "경기도 거주 만 18세~39세 구직 청년",
                    "amount": "면접 1회당 5만 원 (연 최대 10회, 총 50만 원 지역화폐)",
                    "deadline": "하반기 지정 접수 기간",
                    "end_date": "2026-12-31",
                    "apply_path": "잡아바 어플라이 온라인 신청",
                    "secret_tip": "이직 준비 중인 단기 알바생, 지방 소재 기업 면접 본 경기도 청년도 증빙만 있으면 100% 지급."
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
                    "target": "대전 거주 또는 타 지역에서 대전 이전 예정인 만 19세~39세 무주택 청년",
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

    # 1. 과거 작성된 모든 게시글의 전체 텍스트 수집 (중복 검사용)
    all_past_text = ""
    if os.path.exists("posts.json"):
        try:
            with open("posts.json", "r", encoding="utf-8") as f:
                posts_data = json.load(f)
                for post in posts_data:
                    all_past_text += post.get("content", "") + "\n"
        except Exception as e:
            print(f"⚠️ posts.json 읽기 오류: {e}")

    if os.path.exists("posts"):
        try:
            for fname in os.listdir("posts"):
                if fname.endswith(".md"):
                    fpath = os.path.join("posts", fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        all_past_text += f.read() + "\n"
        except Exception as e:
            print(f"⚠️ posts 폴더 스캔 오류: {e}")

    # 2. [우선순위 1] 온통청년 API 호출 시도
    api_subsidies = fetch_from_youth_center_api()
    if api_subsidies:
        # 과거 포스팅 본문에 제목이 없는 신규 지원금 선별
        unposted_api = [s for s in api_subsidies if s["title"] not in all_past_text]
        
        if unposted_api:
            selected_count = min(3, len(unposted_api))
            selected_subsidies = random.sample(unposted_api, selected_count)
            print(f"✨ [온통청년 API] 미발행 신규 지원금 {selected_count}개를 정상 선택했습니다!")
            return {
                "scope_type": "national",
                "region_name": "전국/지자체",
                "subsidies": selected_subsidies
            }
        else:
            selected_count = min(3, len(api_subsidies))
            selected_subsidies = random.sample(api_subsidies, selected_count)
            print("🔄 [온통청년 API] 수집된 모든 지원금이 작성되어 재순환 선택했습니다.")
            return {
                "scope_type": "national",
                "region_name": "전국/지자체",
                "subsidies": selected_subsidies
            }

    # 3. [우선순위 2] API 실패 시 내장 DB (data_pool) 사용
    print("💡 온통청년 API 미발동으로 내장 DB에서 선택합니다.")
    valid_data_pool = []
    for group in data_pool:
        valid_subsidies = [s for s in group["subsidies"] if is_subsidy_valid(s)]
        if valid_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = valid_subsidies
            valid_data_pool.append(group_copy)

    unposted_data_pool = []
    for group in valid_data_pool:
        # 본문 전체 텍스트에 제목이 없는 지원금 그룹만 추출
        unposted_subsidies = [s for s in group["subsidies"] if s["title"] not in all_past_text]
        if unposted_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = unposted_subsidies
            unposted_data_pool.append(group_copy)

    if unposted_data_pool:
        selected_data = random.choice(unposted_data_pool)
        print("✨ [내장 DB] 아직 작성하지 않은 새로운 지원금을 선택했습니다.")
    elif valid_data_pool:
        selected_data = random.choice(valid_data_pool)
        print("🔄 [내장 DB] 모든 지원금이 작성되어 재순환 선택했습니다.")
    else:
        selected_data = data_pool[-1]

    return selected_data

# 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
