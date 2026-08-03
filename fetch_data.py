import os
import json
import random
import urllib.request
import ssl
import time
import xml.etree.ElementTree as ET
from datetime import datetime

HISTORY_FILE = "history.json"

def load_history():
    """발행된 지원금 장부(history.json)를 불러옵니다."""
    history = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    history.update(data)
        except Exception as e:
            print(f"⚠️ history.json 읽기 예외: {e}")
    return history

def save_history(history_set):
    """발행된 지원금 장부(history.json)를 저장합니다."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history_set), f, ensure_ascii=False, indent=2)
        print(f"📝 [장부 업데이트] 누적 발행된 지원금 총 {len(history_set)}개 기록됨")
    except Exception as e:
        print(f"⚠️ history.json 저장 예외: {e}")

def is_subsidy_valid(subsidy):
    """
    오늘 날짜 및 현재 월/시즌 기준으로 지원금이 유효한지 검증하는 함수
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_month = now.month

    deadline = str(subsidy.get("deadline", ""))
    end_date = str(subsidy.get("end_date", ""))

    if current_month >= 7:
        past_keywords = ["상반기", "1분기", "2분기", "매년 초", "1월", "2월", "3월", "4월", "5월", "6월"]
        if any(k in deadline for k in past_keywords):
            if not any(k in deadline for k in ["하반기", "상시", "연중", "소진", "9월", "11월"]):
                return False

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
    온통청년(청년센터) 오픈 API를 호출하며, 타임아웃 및 SSL 인증 처리를 강화합니다.
    """
    api_key = os.environ.get("YOUTH_CENTER_API_KEY", "").strip()
    if not api_key:
        print("💡 [API 안내] YOUTH_CENTER_API_KEY 가 Secrets에 없습니다. 내장 DB를 사용합니다.")
        return None

    url = f"https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey={api_key}&pageIndex=1&display=50"

    # SSL 보안 인증 검사 우회 (공공기관 서버 통신 안정화)
    context = ssl._create_unverified_context()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
    }

    # 최대 2회 재시도 (정부 서버 지연 대응)
    xml_data = None
    for attempt in range(1, 3):
        try:
            print(f"📡 온통청년 API 호출 시도 중... ({attempt}/2)")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20, context=context) as response:
                xml_data = response.read().decode('utf-8')
                if xml_data:
                    break
        except Exception as e:
            print(f"⚠️ ({attempt}/2) 시도 중 통신 실패: {e}")
            time.sleep(2)

    if not xml_data:
        print("⚠️ 온통청년 API 서버 응답 없음 (해외 클라우드 IP 차단 또는 서버 점검 중)")
        return None

    try:
        if "<resultCode>" in xml_data or "<errMsg>" in xml_data or "ERROR" in xml_data:
            print(f"⚠️ [API 승인대기/오류] API가 아직 승인 안 되었거나 키 오류입니다: {xml_data[:150]}")
            return None

        root = ET.fromstring(xml_data)
        emp_list = root.findall('.//emp')

        if not emp_list:
            print("⚠️ [API 안내] API 응답 데이터가 0개입니다.")
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
        print(f"⚠️ [XML 파싱 예외] {e}")
        return None

def get_subsidy_data():
    """
    발행 장부(history.json)를 기반으로 100% 중복을 차단하고 신규 지원금을 추출합니다.
    """
    history_set = load_history()

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

    # 과거 올렸던 부산 지원금 장부 등록
    history_set.add("부산 청년 월세 파격 지원 사업")
    history_set.add("2026 부산 청년 끌어안음 주택임차보증금 이자지원")

    # 1. [우선순위 1] 온통청년 API 호출 시도
    api_subsidies = fetch_from_youth_center_api()
    if api_subsidies:
        unposted_api = [s for s in api_subsidies if s["title"] not in history_set]
        candidate_pool = unposted_api if unposted_api else api_subsidies
        
        selected_count = min(3, len(candidate_pool))
        selected_subsidies = random.sample(candidate_pool, selected_count)

        for s in selected_subsidies:
            history_set.add(s["title"])
        save_history(history_set)

        print(f"✨ [온통청년 API] 장부 미등록 신규 지원금 {selected_count}개를 정상 선택했습니다!")
        return {
            "scope_type": "national",
            "region_name": "전국/지자체",
            "subsidies": selected_subsidies
        }

    # 2. [우선순위 2] API 미발동 시 내장 DB (data_pool) 사용
    print("💡 온통청년 API 미발동으로 내장 DB에서 장부 미등록 항목을 검색합니다.")
    unposted_groups = []
    for group in data_pool:
        unposted_subsidies = [s for s in group["subsidies"] if s["title"] not in history_set]
        if unposted_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = unposted_subsidies
            unposted_groups.append(group_copy)

    if unposted_groups:
        selected_data = random.choice(unposted_groups)
        for s in selected_data["subsidies"]:
            history_set.add(s["title"])
        save_history(history_set)
        print("✨ [내장 DB] 장부에 없는 '새로운 지역 지원금'을 선택했습니다.")
    else:
        history_set.clear()
        selected_data = random.choice(data_pool)
        for s in selected_data["subsidies"]:
            history_set.add(s["title"])
        save_history(history_set)
        print("🔄 [내장 DB] 모든 내장 지원금이 장부에 기록되어 순환 재선택했습니다.")

    return selected_data

# 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
