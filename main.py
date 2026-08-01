import os
import json
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 1. fetch_data 모듈 안전 임포트 (get_subsidy_data 및 fetch_subsidy_data 모두 지원)
try:
    from fetch_data import get_subsidy_data
except Exception:
    try:
        from fetch_data import fetch_subsidy_data as get_subsidy_data
    except Exception:
        def get_subsidy_data():
            return {
                "scope_type": "national",
                "region_name": "전국 공통",
                "subsidies": [{
                    "title": "2026 청년도약계좌",
                    "target": "만 19~34세 청년",
                    "amount": "최대 5,000만 원 목돈 마련",
                    "deadline": "상시 접수"
                }]
            }

# 2. generate_report 모듈 안전 임포트
try:
    from generate_report import generate_seo_markdown
except Exception:
    def generate_seo_markdown(data):
        return "# 2026 청년 알짜 지원금 안내\n\n최신 청년 지원금 리포트입니다."

def get_korean_font(size, is_bold=False):
    """
    GitHub Actions 리눅스 서버에 한글 폰트가 없을 때
    구글 폰트(나눔고딕)를 구글 공식 저장소에서 자동 다운로드하여 적용합니다.
    """
    font_filename = "NanumGothic-Bold.ttf" if is_bold else "NanumGothic-Regular.ttf"
    font_path = os.path.join(".", font_filename)

    if not os.path.exists(font_path):
        url = (
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
            if is_bold else
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        )
        try:
            print(f"📥 한글 폰트 자동 다운로드 실행: {font_filename}")
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            print(f"⚠️ 폰트 다운로드 실패: {e}")

    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def create_summary_table_image(data, output_path):
    """
    수집된 지원금 데이터를 바탕으로 요약 카드뉴스 이미지(PNG)를 자동 생성합니다.
    """
    subsidies = data.get("subsidies", [])
    if not subsidies:
        return None

    # 이미지 기본 규격 설정
    img_width = 850
    card_height = 120
    header_height = 90
    padding = 20
    img_height = header_height + (len(subsidies) * card_height) + padding

    # 연한 회색 배경 캔버스 생성
    image = Image.new("RGB", (img_width, img_height), color="#F8FAFC")
    draw = ImageDraw.Draw(image)

    # 폰트 불러오기 (나눔고딕 자동 적용으로 한글 깨짐 원천 방지)
    title_font = get_korean_font(21, is_bold=True)
    card_title_font = get_korean_font(16, is_bold=True)
    text_font = get_korean_font(14, is_bold=False)
    bold_font = get_korean_font(15, is_bold=True)

    # 상단 헤더 박스 생성 (어두운 블루계열)
    draw.rectangle([(0, 0), (img_width, header_height - 10)], fill="#1E293B")
    region_name = data.get("region_name", "전국")
    draw.text((30, 25), f"🔔 [{region_name}] 핵심 청년 지원금 한눈에 보기", fill="#FFFFFF", font=title_font)

    # 지원금 항목별 카드 렌더링
    y_offset = header_height
    for idx, item in enumerate(subsidies, 1):
        # 흰색 라운드 카드
        draw.rectangle(
            [(20, y_offset), (img_width - 20, y_offset + card_height - 15)],
            fill="#FFFFFF",
            outline="#E2E8F0",
            width=2
        )

        title_text = f"{idx}. {item.get('title', '청년 지원금')}"
        target_text = f"• 대상: {item.get('target', '청년')}"
        amount_text = f"• 혜택: {item.get('amount', '지자체 공고 참조')}"
        deadline_text = f"• 마감: {item.get('deadline', '상시/지정기간')}"

        draw.text((40, y_offset + 12), title_text, fill="#0F172A", font=card_title_font)
        draw.text((40, y_offset + 40), target_text, fill="#475569", font=text_font)
        draw.text((40, y_offset + 65), amount_text, fill="#2563EB", font=bold_font) # 혜택 강조 색상
        draw.text((520, y_offset + 65), deadline_text, fill="#DC2626", font=bold_font) # 마감 강조 색상

        y_offset += card_height

    # 폴더가 없으면 생성 후 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, "PNG")
    print(f"📸 요약 카드 이미지 생성 완료: {output_path}")
    return output_path

def main():
    # 1) 지원금 데이터 가져오기
    raw_data = get_subsidy_data()
    
    if isinstance(raw_data, list):
        data = raw_data[0] if len(raw_data) > 0 else {}
    elif isinstance(raw_data, dict):
        data = raw_data
    else:
        data = {}

    now_str = datetime.now().strftime("%Y-%m-%d-%H%M%S")

    # 2) 요약 카드 이미지 자동 생성
    img_filename = f"{now_str}-summary.png"
    img_path = os.path.join("images", img_filename)
    created_img = create_summary_table_image(data, img_path)

    # 3) AI 마크다운 포스팅 생성
    markdown_content = generate_seo_markdown(data)

    # 4) 마크다운 본문에 이미지 태그 자동 결합
    if created_img:
        image_tag = f"\n\n![{data.get('region_name', '청년')} 지원금 요약 비교표](./images/{img_filename})\n\n"
        if "30초 요약" in markdown_content:
            parts = markdown_content.split("30초 요약", 1)
            first_newline = parts[1].find("\n\n")
            if first_newline != -1:
                markdown_content = parts[0] + "30초 요약" + parts[1][:first_newline] + image_tag + parts[1][first_newline:]
            else:
                markdown_content = parts[0] + "30초 요약" + image_tag + parts[1]
        else:
            markdown_content = image_tag + markdown_content

    # 5) posts/ 폴더에 마크다운 작성 및 저장
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{now_str}-subsidy-report.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"📝 마크다운 포스팅 작성 완료: {filename}")

    # 6) posts.json 파일 업데이트
    posts_list = []
    if os.path.exists("posts"):
        files = sorted([f for f in os.listdir("posts") if f.endswith(".md")], reverse=True)
        for f_name in files:
            file_path = os.path.join("posts", f_name)
            with open(file_path, "r", encoding="utf-8") as f:
                posts_list.append({
                    "filename": f_name,
                    "content": f.read()
                })

    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(posts_list, f, ensure_ascii=False, indent=2)

    print("✅ posts.json 데이터 파일 업데이트 성공!")

if __name__ == "__main__":
    main()
