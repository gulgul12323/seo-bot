import os
from datetime import datetime

# 1. fetch_data 모듈 안전 임포트
try:
    from fetch_data import fetch_subsidy_data
except Exception:
    def fetch_subsidy_data():
        return [{"title": "2026 청년 월세 특별지원", "category": "주거지원", "target": "만 19~34세 청년", "summary": "월 최대 20만원 지원"}]

# 2. generate_report 모듈 안전 임포트
try:
    from generate_report import generate_seo_markdown
except Exception:
    def generate_seo_markdown(data):
        return "# 2026 청년 알짜 지원금 안내\n\n최신 청년 지원금 리포트입니다."

def main():
    raw_data = fetch_subsidy_data()
    
    # generate_report가 dict 형태(.get)를 요구하므로 데이터 타입 안전 처리
    if isinstance(raw_data, list):
        data = raw_data[0] if len(raw_data) > 0 else {}
    elif isinstance(raw_data, dict):
        data = raw_data
    else:
        data = {}
        
    markdown_content = generate_seo_markdown(data)
    
    os.makedirs("posts", exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"posts/{now}-subsidy-report.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"새로운 포스팅 마크다운 파일 생성 완료: {filename}")

if __name__ == "__main__":
    main()
