from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name='dfg1cai07',  # ⚠️ 請改成你的 Cloudinary 名稱
    api_key='475588673538526',
    api_secret='YgY9UqhPTxuRdBi7PcFvYnfH4V0'
)

font_path = "NotoSansTC-VariableFont_wght.ttf"
if not os.path.exists(font_path):
    raise FileNotFoundError("Font file not found.")
font = ImageFont.truetype(font_path, 48)

def generate_image_with_photo_overlay(text, image_url, index, font=font):
    size = 1080
    try:
        response = requests.get(image_url, timeout=5)
        bg_image = Image.open(BytesIO(response.content)).convert("RGB")
        bg_image = bg_image.resize((size, size))
    except:
        bg_image = Image.new("RGB", (size, size), (255, 255, 255))

    draw = ImageDraw.Draw(bg_image)

    lines = text.split("\n")
    line_height = draw.textbbox((0, 0), lines[0], font=font)[3] + 10
    total_height = line_height * len(lines)
    text_y = size - total_height - 50

    overlay = Image.new("RGBA", bg_image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, text_y - 20), (size, text_y + total_height + 20)], fill=(0, 0, 0, 150))
    bg_image = Image.alpha_composite(bg_image.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(bg_image)
    for line in lines:
        text_width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((size - text_width) // 2, text_y), line, font=font, fill=(255, 255, 255))
        text_y += line_height

    image_bytes = BytesIO()
    bg_image.convert("RGB").save(image_bytes, format='PNG')
    image_bytes.seek(0)

    upload_response = cloudinary.uploader.upload(
        image_bytes,
        public_id=f"centanet_{index}",
        overwrite=True
    )
    return upload_response["secure_url"]

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Centanet Rent Scraper is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    try:
        # === Setup headless Chrome ===
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")  # Important!
        options.add_argument("--single-process")
        options.add_argument("--window-size=1920x1080")

        driver = webdriver.Chrome(options=options)
        driver.get("https://hk.centanet.com/findproperty/list/rent")
        time.sleep(3)

        listings_data = []

        # === Scroll to trigger lazy-loaded data ===
        scroll_pause = 0.25
        scroll_y = 500
        current_y = 0
        max_y = driver.execute_script("return document.body.scrollHeight")

        while current_y < max_y:
            driver.execute_script(f"window.scrollTo(0, {current_y});")
            time.sleep(scroll_pause)
            current_y += scroll_y
            max_y = driver.execute_script("return document.body.scrollHeight")

        # === Parse page ===
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        for idx, card in enumerate(listings):
            try:
                title_tag = card.select_one("span.title-lg")
                if not title_tag or not title_tag.text.strip():
                    continue

                title = title_tag.text.strip()
                subtitle = card.select_one("span.title-sm")
                subtitle = subtitle.text.strip() if subtitle else ""

                area = card.select_one("div.area")
                area = area.text.strip() if area else ""

                usable_tag = card.select_one("div.area-block.usable-area div.num > span.hidden-xs-only")
                usable_area = usable_tag.get_text(strip=True).replace("呎", "").replace(",", "") if usable_tag else ""

                construction_tag = card.select_one("div.area-block.construction-area div.num > span.hidden-xs-only")
                construction_area = construction_tag.get_text(strip=True).replace("呎", "").replace(",", "") if construction_tag else ""

                rent_tag = card.select_one("span.price-info")
                rent = rent_tag.get_text(strip=True).replace(",", "").replace("$", "") if rent_tag else ""

                image_tag = card.select_one("img")
                image_url = image_tag.get("src") if image_tag else ""

                summary = f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎 建築: {construction_area}呎\n租金: ${rent}"
                pic_generated = generate_image_with_photo_overlay(summary, image_url, idx)

                listings_data.append({
                    "title": title,
                    "subtitle": subtitle,
                    "area": area,
                    "usable_area": usable_area,
                    "construction_area": construction_area,
                    "rent": rent,
                    "image_url": image_url,
                    "summary": summary,
                    "pic_generated": pic_generated
                })

            except Exception as e:
                listings_data.append({
                    "title": "❌ Error parsing listing",
                    "summary": str(e)
                })

        driver.quit()
        return jsonify({"listings": listings_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
