import json
import random
from datetime import datetime

def is_subsidy_valid(subsidy):
    """
    오늘 날짜 기준으로 지원금이 유효한지 검증하는 함수
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. end_date(마감일자)가 명시되어 있는 경우 날짜 직접 비교
    end_date = subsidy.get("end_date")
    if end_date:
        if any(k in str(end_date) for k in ["상시", "연중", "소진", "매월", "분기"]):
            return True
        try:
            return str(end_date) >= today_str
        except Exception:
            return True

    # 2. deadline 텍스트에 마감/종료 표기가 있는지 검증
    deadline = str(subsidy.get("deadline", ""))
    
    # '소진 시 마감', '상시 접수'는 유효하지만, 단순 '마감' 또는 '접수 종료'는 제외
    if any(k in deadline for k in ["접수 마감", "모집 종료", "선발 완료"]):
        if "소진 시" not in deadline and "상시" not in deadline:
            return False
            
    return True

def get_subsidy_data():
    """
    전국 광역/기초 지자체 및 중앙부처의 고가치(High-Value) 청년 지원금 DB
    혜택 금액이 크거나 틈새 유용성이 높은 정보만 선별하여 무작위 추출합니다.
    """
    data_pool = [
        # [부산광역시]
        {
            "scope_type": "local",
            "region_name": "부산광역시",
            "subsidies": [
                {
                    "title": "2026 부산 청년 기쁨두배통장 (자산형성 지원)",
                    "target": "부산 거주 만 18세~39세 일하는 청년 (기준중위소득 140% 이하)",
                    "amount": "2년/3년 적립 시 저축액의 100% 매칭 지원 (최대 540만 원+이자)",
                    "deadline": "상반기 지정 모집 기간 (선발제)",
                    "end_date": "2026-12-31",
                    "apply_path": "부산청년기쁨두배통장 전용 홈페이지",
                    "secret_tip": "부모 소득을 보지 않고 '청년 본인 소득'만 검증하므로, 자취하는 직장인/프리랜서 선정률 매우 높음."
                },
                {
                    "title": "부산 청년 월세 파격 지원 사업",
                    "target": "부산 거주 무주택 청년 가구주 (임차보증금 1억 원 이하)",
                    "amount": "월 최대 20만 원 (연 최대 240만 원 환급)",
                    "deadline": "상시 접수 (예산 소진 시 마감)",
                    "end_date": "상시",
                    "apply_path": "부산청년플랫폼 온라인 접수",
                    "secret_tip": "국토부 청년월세 특별지원과 중복은 안 되지만, 소득 기준이 더 완화되어 국토부 탈락자가 신청하기 최적."
                }
            ]
        },

        # [경기도]
        {
            "scope_type": "local",
            "region_name": "경기도",
            "subsidies": [
                {
                    "title": "2026 경기도 청년 기본소득 (분기별 지급)",
                    "target": "경기도에 3년 이상 연속 거주 중인 만 24세 청년",
                    "amount": "분기별 25만 원 (연 총 100만 원, 지역화폐 지급)",
                    "deadline": "매 분기(3월, 6월, 9월, 11월) 접수",
                    "end_date": "2026-11-30",
                    "apply_path": "경기도 잡아바 어플라이(apply.jobaba.net)",
                    "secret_tip": "소득/재산/취업 여부 전혀 안 봄! 만 24세 나이 조건만 맞으면 100% 지급하는 경기 청년 전용 돈."
                },
                {
                    "title": "경기도 청년 면접수당 (역대 최대 규모)",
                    "target": "경기도 거주 만 18세~39세 구직 청년",
                    "amount": "면접 1회당 5만 원 (연 최대 10회, 총 50만 원 지역화폐)",
                    "deadline": "상/하반기 지정 접수 기간",
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
                    "secret_tip": "대전 시내 대학가(충남대, 한남대 등) 주변 자취방 구할 때 은행 대출이자 부담을 거의 0원으로 만듦."
                },
                {
                    "title": "충남 청년 농업·창업 지원금",
                    "target": "충남 거주 만 19세~39세 영농/창업 희망 청년",
                    "amount": "3년간 월 최대 110만 원 정착 지원금 지급",
                    "deadline": "매년 초 지정 모집",
                    "end_date": "2026-12-31",
                    "apply_path": "충남 청년포털 및 시군구 청년담당 부서",
                    "secret_tip": "지방 소멸 방지 예산이 집중되어 수도권 대비 경쟁률이 훨씬 낮아 선정 확률 매우 높음."
                }
            ]
        },

        # [전국 공통 - 압도적 혜택 금액]
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
                    "apply_path": "주요 은행(KB, 신한, 우리, 하나 등) 모바일 앱",
                    "secret_tip": "육아휴직자, 육아수당 수령자도 가입 가능하며, 육아/병역 이행 기간은 나이 산정 시 차감해 줌."
                },
                {
                    "title": "2026 K-Digital Training (KDT) IT/AI 교육비 전액 지원",
                    "target": "구직자(대학생, 취준생, 이직희망자)",
                    "amount": "수강료 100% 전액 국비지원 (수백만 원 상당) + 월 최대 31만 6천 원 훈련수당 지급",
                    "deadline": "상시 과정 개설",
                    "end_date": "상시",
                    "apply_path": "HRD-Flex 및 고용24 홈페이지 (내일배움카드 발급 필수)",
                    "secret_tip": "전공 상관없이 문과생도 신청 가능. 출석률 80%만 유지하면 수당이 통장으로 들어옴."
                }
            ]
        }
    ]
    
    # 마감된 지원금 1차 걸러내기
    valid_data_pool = []
    for group in data_pool:
        valid_subsidies = [s for s in group["subsidies"] if is_subsidy_valid(s)]
        if valid_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = valid_subsidies
            valid_data_pool.append(group_copy)
            
    # 유효한 그룹 중 무작위 1개 추출 (없을 경우 기본 그룹 반환)
    if valid_data_pool:
        selected_data = random.choice(valid_data_pool)
    else:
        selected_data = data_pool[-1] # 전국 공통 기본값
        
    return selected_data

# 모듈 호출 호환성을 위한 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
