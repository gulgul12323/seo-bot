import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def generate_seo_markdown(data):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
        return "# 2026 청년 지원금 안내\n\n최신 지원금 리포트를 준비 중입니다."

    client = OpenAI(api_key=api_key)

    # 오늘 날짜 정보 구하기
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_korean = datetime.now().strftime("%Y년 %m월 %d일")

    scope_type = data.get("scope_type", "national")
    region_name = data.get("region_name", "전국")

    # 제목 어그로 극대화 가이드라인
    if scope_type == "local":
        title_instruction = f"[{region_name} 2030 청년 필독]을 포함해 클릭하지 않고는 못 배기는 어그로 제목 (예: '[선착순 마감] {region_name} 사는 청년 90%가 몰라서 버리는 숨은 돈 50만 원')"
    else:
        title_instruction = "2030 청년 자취생·취준생 통장을 뒤흔드는 강력한 후킹형 제목 (예: '아직도 내 돈 다 내고 사나요? 모르면 40만 원 버리는 2030 청년 알짜 지원금 2가지')"

    prompt = f"""
    너는 2030 청년들과 가장 친근하게 소통하는 혜택 정보 전문 에디터야.
    오늘 날짜는 **{today_korean} ({today_str})** 이다.
    아래 수집 데이터를 바탕으로, 읽는 재미가 있고 3초 만에 시선을 사로잡는 마크다운 블로그 포스트를 작성해 줘.

    [수집 데이터]
    타겟: {region_name} ({scope_type})
    내용: {json.dumps(data.get("subsidies", []), ensure_ascii=False, indent=2)}

    [🚨 마감일 및 날짜 정보 날조 절대 금지 지침]
    1. 데이터에 특정 마감일자(예: YYYY-MM-DD)가 명시되어 있지 않다면, **절대로 임의의 마감일자(예: 2026년 12월 31일 등)를 지어내거나 추측해서 적지 말 것!**
    2. 마감일이 명확하지 않은 경우 반드시 **"상시 모집 (예산 소진 시 조기 마감)", "지자체/기관 개별 공고 참조", "분기별 지정 기간 접수"** 등으로만 표기할 것.
    3. 오늘 날짜({today_korean})를 기준으로 이미 확실히 신청 기한이 지난 지원금은 포스팅 대상에서 완전히 제외할 것.

    [작성 규칙 - 엄격 적용]
    1. **제목 어그로 극대화:** 
       - 가이드라인: {title_instruction}
       - 숫자를 명확히 드러내고, 안 읽으면 나만 손해 보는 듯한 위기감과 궁금증을 동시에 자극할 것.

    2. **친근하고 감기는 어조(Tone):**
       - 마치 친한 선배가 조언해주듯 친근하고 싹싹한 존댓말('~해요', '~거든요!', '~해보세요', '~죠?') 사용!
       - 공무원이나 서류 안내문 같은 딱딱하고 단정한 어조 절대 금지.
       - "자취하면서 이 돈 안 챙기면 너무 아깝잖아요!"처럼 청년들의 현실적인 상황에 깊이 공감해 줄 것.

    3. **서식(Formatting) 제한:**
       - 본문 텍스트 내 ** (볼드) 기호를 남발하지 말 것.
       - 가시성은 인용구(>), 제목 태그(##, ###), 번호 리스트로만 깔끔하게 확보할 것.

    4. **체류 시간 극대화 필수 내용 (지원금마다 구체적으로 작성):**
       - [시뮬레이션 예시]: 2030 청년 가상 인물(예: 26세 취준생 A씨)의 실제 수혜 금액을 숫자로 계산해 주기.
       - [서류 체크리스트 & 발급처]: 서류 이름과 온라인 발급처(정부24, 대법원, 홈택스 등) 상세 안내.
       - [실제 탈락 사례 & 꿀팁]: 독자들이 실제 반려당하는 안타까운 사유와 해결 예방법.
       - [신청 경로 1-2-3]: 접속 사이트/앱 이름과 신청 클릭 메뉴 순서 가이드.

    [포스트 필수 구성]
    - YAML Frontmatter (title, description, date, tags)
    - ## 🚨 30초 요약: 안 받아가면 진짜 손해 보는 꿀혜택
    - ## 💡 지원금별 정밀 분석 & 신청 가이드
       * 각 지원금마다 ### 1. [지원금명] 구조로 작성
       * 지원 대상 및 핵심 조건
       * 💰 실제 수혜 금액 시뮬레이션 계산 예시
       * 📄 필수 제출 서류 목록 & 온라인 발급처
       * ⚠️ 가장 많이 탈락하는 실제 실수 사례 & 꿀팁
       * 🔗 신청 경로 & 단계별 방법 (Step-by-Step)
    - ## 📊 한눈에 보는 혜택 조건 비교표
    - ## ❓ 자주 묻는 질문 FAQ (실질적 질문 2개)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI API 호출 실패: {e}")
        return f"# [{region_name}] 2030 청년 지원금 소식\n\n최신 청년 지원금 정보를 준비 중입니다."
