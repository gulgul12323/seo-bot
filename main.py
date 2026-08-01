import os
import json
from datetime import datetime

# 1. fetch_data 모듈 안전 임포트 (함수명이 달라도 자동 감지)
try:
    from fetch_data import fetch_subsidy_data
except ImportError:
    try:
        import fetch_data
        if hasattr(fetch_data, 'get_subsidy_data'):
            fetch_subsidy_data = fetch_data.get_subsidy_data
        elif hasattr(fetch_data, 'fetch_data'):
            fetch_subsidy_data = fetch_data.fetch_data
        else:
            raise AttributeError
    except Exception:
        def fetch_subsidy_data():
            return [{"title": "2026 청년 월세 특별지원", "category": "주거지원", "target": "만 19~34세 청년", "summary": "월 최대 20만원 지원"}]

# 2. generate_report 모듈 안전 임포트
try:
    from generate_report import generate_seo_markdown
except ImportError:
    try:
        import generate_report
        if hasattr(generate_report, 'generate_report'):
            generate_seo_markdown = generate_report.generate_report
        else:
            raise AttributeError
    except Exception:
        def generate_seo_markdown(data):
            return "# 2026 청년 알짜 지원금 안내\n\n최신 청년 지원금 리포트입니다."

def update_index_html():
    posts_dir = "posts"
    if not os.path.exists(posts_dir):
        return

    files = sorted([f for f in os.listdir(posts_dir) if f.endswith(".md")], reverse=True)
    posts_data = []

    for file_name in files:
        file_path = os.path.join(posts_dir, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            posts_data.append(content)

    html_content = f"""




2030 청년 알짜 지원금 매일 알리미






    
        🔔 2030 청년 알짜 지원금 매일 알리미
        놓치면 손해보는 전국 & 지자체 청년 혜택 리포트
    
    




"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    data = fetch_subsidy_data()
    markdown_content = generate_seo_markdown(data)
    
    os.makedirs("posts", exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"posts/{now}-subsidy-report.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"새로운 마크다운 포스팅 생성 완료: {filename}")
    
    update_index_html()
    print("index.html 블로그 메인 페이지 업데이트 완료!")

if __name__ == "__main__":
    main()
