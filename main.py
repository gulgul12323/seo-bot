import os
import json
from datetime import datetime
from fetch_data import fetch_subsidy_data
from generate_report import generate_seo_markdown

def update_index_html():
    posts_dir = "posts"
    if not os.path.exists(posts_dir):
        return

    # 최신 포스팅 순으로 파일 정렬
    files = sorted([f for f in os.listdir(posts_dir) if f.endswith(".md")], reverse=True)
    posts_data = []

    for file_name in files:
        file_path = os.path.join(posts_dir, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            posts_data.append(content)

    # index.html 메인 블로그 웹페이지 생성
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
    
    # 메인 웹페이지(index.html) 자동 업데이트
    update_index_html()
    print("index.html 블로그 메인 페이지 업데이트 완료!")

if __name__ == "__main__":
    main()