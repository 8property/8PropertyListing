from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time, os, requests
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from io import BytesIO
import cloudinary
import cloudinary.uploader

# === Cloudinary Config ===
cloudinary.config(
    cloud_name='dfg1cai07',
    api_key='475588673538526',
    api_secret='YgY9UqhPTxuRdBi7PcFvYnfH4V0'
)

# === Font Config ===
font_path = "NotoSansTC-VariableFont_wght.ttf"
font = ImageFont.truetype(font_path, 48)

app = Flask(__name__)

def generate_image_with_photo_overlay(text, image_url, index):
    size = 1080
    try:
        response = requests.get(image_url.strip(), timeout=5)
        bg_image = Image.open(BytesIO(response.content)).convert("RGB").resize((size, size))
    except:
        bg_image = Image.new("RGB", (size, size), (255, 255, 255))

    draw = ImageDraw.Draw(bg_image)
    lines = text.split("\n")
    line_height = draw.textbbox((0, 0), lines[0], font=font)[3] + 10
    total_height = line_height * len(lines)
    text_y = size - total_height - 50

    overlay = Image.new("RGBA", bg_image.size, (0, 0, 0, 150))
    ImageDraw.Draw(overlay).rectangle([(0, text_y - 20), (size, text_y + total_height + 20)], fill=(0, 0, 0, 150))
    bg_image = Image.alpha_composite(bg_image.convert("RGBA"), overlay)

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

def scrape_listings():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=options)
    driver.get("https://hk.centanet.com/findproperty/list/rent")

    try:
        # Remove overlay
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.deepLink-main"))
            )
            driver.execute_script("arguments[0].remove();", overlay)
        except:
            pass

        # Select 最新放盤
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        driver.execute_script("arguments[0].click();", dropdown_trigger)
        time.sleep(0.5)
        dropdown_items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in dropdown_items:
            if "最新放盤" in item.text.strip():
                driver.execute_script("arguments[0].click();", item)
                time.sleep(2)
                break

        # Scroll
        for i in range(15):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(0.8)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        results = []
        for idx, card in enumerate(listings[:15]):
            title_tag = card.select_one("span.title-lg")
            if not title_tag or not title_tag.text.strip():
                continue

            title = title_tag.text.strip()
            subtitle = card.select_one("span.title-sm").text.strip() if card.select_one("span.title-sm") else ""
            area = card.select_one("div.area").text.strip() if card.select_one("div.area") else ""
            usable_tag = card.select_one("div.area-block.usable-area div.num > span.hidden-xs-only")
            usable_area = usable_tag.get_text(strip=True).replace("呎", "").replace(",", "") if usable_tag else ""
            rent_tag = card.select_one("span.price-info")
            rent = f"${int(rent_tag.get_text(strip=True).replace(',', '').replace('$', '')):,}" if rent_tag else ""

            image_url = ""
            img_tag = card.select_one("div.el-image.img-holder img")
            if img_tag:
                src = img_tag.get("data-src") or img_tag.get("src", "")
                if ".jpg" in src and src.startswith("http"):
                    image_url = src.split("?")[0].strip()

            results.append({
                "title": title,
                "subtitle": subtitle,
                "area": area,
                "usable_area": usable_area,
                "rent": rent,
                "image_url": image_url,
                "summary": f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎 \n租金: {rent}",
                "pic_generated": ""  # initially empty
            })

        return results

    finally:
        driver.quit()

def upload_to_cloudinary_async(listings):
    for idx, item in enumerate(listings):
        if item["image_url"]:
            try:
                item["pic_generated"] = generate_image_with_photo_overlay(item["summary"], item["image_url"], idx)
            except Exception as e:
                print(f"⚠️ Cloudinary upload failed for {item['title']}: {e}")

@app.route("/run", methods=["GET"])
def run_scraper():
    listings = scrape_listings()
    Thread(target=upload_to_cloudinary_async, args=(listings,)).start()
    return jsonify({"listings": listings})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
