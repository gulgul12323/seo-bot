import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_seo_markdown(data):
    today = datetime.now().strftime("%Y-%m-%d")
    scope_type = data.get("scope_type", "national")
    region_name = data.get("region_name", "전국")

    prompt = f"""
    너는 2030 청년들이 가장 읽기 편해하는 지원금 전문 에디터야.
    아래 데이터를 바탕으로, 사람이 직접 쓴 것처럼 자연스럽고 매끄러운 마크다운 블로그 포스트를 작성해 줘.

    [수집 데이터]
    타겟: {region_name} ({scope_type})
    내용: {json.dumps(data.get("subsidies", []), ensure_ascii=False, indent=2)}

    [어조 및 금지 규칙 - 엄격 준수!]
    1. 어조(Tone): 무조건 100% 친근하고 깔끔한 존댓말('~해요', '~합니다')로만 작성할 것. 
       - 절대로 반말('~다', '~해라', '너')과 존댓말을 섞어 쓰지 마라.
    2. 서식(Formatting) 제한:
       - 문장 중간에 ** (볼드) 기호를 남발하지 마라. AI가 쓴 티가 너무 심하게 난다.
       - 본문 텍스트에는 볼드 기호를 쓰지 말고, 가시성은 인용구(>)와 제목 태그(##, ###)로만 확보해라.
    3. 말투 스타일: "안녕하세요 여러분~" 같은 뻔한 인사는 빼고, 첫 문장부터 바로 핵심 혜택을 짚으며 자연스럽게 시작해라.

    [포스트 구성]
    - YAML Frontmatter (title, description, date, tags)
    - ## 🚨 모르면 손해 보는 핵심 지원금 요약
    - ## 💡 지원금 상세 혜택 및 신청 가이드
      * 각 지원금마다 ### 1. [지원금명] 구조로 작성
      * 지원 대상, 혜택 금액, 신청 기간, 신청 경로(어디서 신청하는지) 포함
      * 담당자만 아는 꿀팁(secret_tip)을 자연스러운 문장으로 녹여낼 것
    - ## 📊 한눈에 보는 요약 비교표
    - ## ❓ 자주 묻는 질문 FAQ (2개)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content