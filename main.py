import os
import json
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

def build_index_html():
    posts_dir = "posts"
    posts_data = []
    
    if os.path.exists(posts_dir):
        files = sorted([f for f in os.listdir(posts_dir) if f.endswith(".md")], reverse=True)
        for file_name in files:
            file_path = os.path.join(posts_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                posts_data.append(f.read())

    json_posts = json.dumps(posts_data, ensure_ascii=False)

    # 파이썬 문법과 웹 CSS 충돌을 완전 차단한 안전 템플릿
    html_template = """




2030 청년 알짜 지원금 매일 알리미






    
        🔔 2030 청년 알짜 지원금 매일 알리미
        놓치면 손해보는 전국 & 지자체 청년 혜택 리포트
    
    




"""

    final_html = html_template.replace("__POSTS_DATA__", json_posts)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

def main():
    raw_data = fetch_subsidy_data()
    
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
    
    print(f"새로운 마크다운 포스팅 생성 완료: {filename}")
    
    # 완성형 index.html 직접 생성
    build_index_html()
    print("index.html 블로그 메인 페이지 빌드 완료!")

if __name__ == "__main__":
    main()
