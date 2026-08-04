import os
import json
import random

def get_already_posted_text():
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

def get_subsidy_data():
    """
    로컬/깃허브에 동기화된 youth_db.json(온통청년 데이터)을 우선 읽어와
    블로그에 올라가지 않은 완전히 새로운 정책을 추출합니다.
    (파일이 없거나 오류 발생 시 내장 백업 DB를 활용합니다.)
    """
    past_text = get_already_posted_text()
    db_file = "youth_db.json"

    # 1. [우선순위 1] youth_db.json 데이터 사용
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                subsidies_pool = json.load(f)

            if subsidies_pool and isinstance(subsidies_pool, list):
                # 블로그에 아직 작성되지 않은 신규 지원금만 선별
                unposted = [s for s in subsidies_pool if s.get("title") and s.get("title") not in past_text]

                if unposted:
                    selected_count = min(3, len(unposted))
                    selected = random.sample(unposted, selected_count)
                    print(f"✨ [온통청년 DB] 미발행 신규 지원금 {selected_count}개 선택 완료!")
                else:
                    selected_count = min(3, len(subsidies_pool))
                    selected = random.sample(subsidies_pool, selected_count)
                    print("🔄 [온통청년 DB] 모든 정책이 작성되어 재순환 선택했습니다.")

                return {
                    "scope_type": "national",
                    "region_name": "전국/지자체 온통청년 정책",
                    "subsidies": selected
                }
        except Exception as e:
            print(f"⚠️ youth_db.json 읽기 예외: {e}")

    # 2. [우선순위 2] youth_db.json 미존재 시 비상 내장 DB 사용
    print("💡 내장 백업 DB에서 중복 없는 신규 지원금을 선택합니다.")
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
                    "apply_path": "청년몽땅정보통 온라인 신청",
                    "secret_tip": "주 30시간 이하 단기 알바생도 신청 가능하며 구직활동 보고서 제출 필수."
                },
                {
                    "title": "서울 청년 대중교통비 지원 사업",
                    "target": "서울 거주 만 19세~24세 청년",
                    "amount": "연 최대 10만 원 교통비 마일리지 환급",
                    "deadline": "상시/지정 모집 기간",
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
                    "apply_path": "부산청년플랫폼 온라인 접수",
                    "secret_tip": "국토부 청년월세 특별지원과 중복은 안 되지만 소득 기준이 더 완화됨."
                },
                {
                    "title": "2026 부산 청년 끌어안음 주택임차보증금 이자지원",
                    "target": "부산 거주 만 19세~39세 무주택 청년",
                    "amount": "대출 연 2.0% 이자 지원 (연 최대 200만 원 절감)",
                    "deadline": "연중 상시 접수",
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
                    "apply_path": "경기도 잡아바 어플라이(apply.jobaba.net)",
                    "secret_tip": "소득/재산/취업 여부 전혀 안 봄! 만 24세 나이 조건만 맞으면 100% 지급."
                },
                {
                    "title": "경기도 청년 면접수당 (역대 최대 규모)",
                    "target": "경기도 거주 만 18세~39세 구직 청년",
                    "amount": "면접 1회당 5만 원 (연 최대 10회, 총 50만 원 지역화폐)",
                    "deadline": "하반기 지정 접수 기간",
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
                    "apply_path": "주요 은행 모바일 앱",
                    "secret_tip": "육아휴직자, 육아수당 수령자도 가입 가능하며 나이 산정 시 군복무 기간 차감."
                },
                {
                    "title": "2026 K-Digital Training (KDT) IT/AI 교육비 전액 지원",
                    "target": "구직자(대학생, 취준생, 이직희망자)",
                    "amount": "수강료 100% 전액 국비지원 + 월 최대 31만 6천 원 훈련수당 지급",
                    "deadline": "상시 과정 개설",
                    "apply_path": "HRD-Flex 및 고용24 홈페이지",
                    "secret_tip": "전공 상관없이 문과생도 신청 가능하며 출석률 80% 이상 시 수당 지급."
                }
            ]
        }
    ]

    unposted_groups = []
    for group in data_pool:
        fresh_subsidies = [s for s in group["subsidies"] if s["title"] not in past_text]
        if fresh_subsidies:
            group_copy = group.copy()
            group_copy["subsidies"] = fresh_subsidies
            unposted_groups.append(group_copy)

    if unposted_groups:
        selected_data = random.choice(unposted_groups)
        print(f"✨ [내장 DB] [{selected_data['region_name']}] 신규 지원금이 선택되었습니다.")
        return selected_data

    print("🔄 [순환 선택] 모든 DB 지원글이 작성되어 순환 선택합니다.")
    return random.choice(data_pool)

# 별칭 설정
fetch_subsidy_data = get_subsidy_data

if __name__ == "__main__":
    data = get_subsidy_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
