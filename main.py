import os
from datetime import datetime
from fetch_data import get_subsidy_data
from generate_report import generate_seo_markdown

def run_pipeline():
    print("1. 2030 청년 (지역/전국) 지원금 데이터 분석 시작...")
    raw_data = get_subsidy_data()
    
    print(f"2. [{raw_data.get('region_name')}] 타겟 AI SEO 포스팅 작성 중...")
    markdown_content = generate_seo_markdown(raw_data)
    
    os.makedirs("./posts", exist_ok=True)
    
    today_slug = datetime.now().strftime("%Y-%m-%d")
    file_path = f"./posts/{today_slug}-subsidy-report.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"3. 성공적으로 저장되었습니다: {file_path}")

if __name__ == "__main__":
    run_pipeline()