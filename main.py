from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import cloudinary
import cloudinary.uploader
import requests
import time
import os
from shutil import which

app = Flask(__name__)

cloudinary.config(
    cloud_name='dfg1cai07',
    api_key='475588673538526',
    api_secret='YgY9UqhPTxuRdBi7PcFvYnfH4V0'
)

font_path = "NotoSansTC-VariableFont_wght.ttf"
font = ImageFont.truetype(font_path, 48)

def generate_image_with_photo_overlay(text, image_url, index):
    size = 1080
    try:
        response = requests.get(image_url.strip(), timeout=5)
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

    for line in lines:
        text_width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((size - text_width) // 2, text_y), line, font=font, fill=(255, 255, 255))
        text_y += line_height

    image_bytes = BytesIO()
    bg_image.convert("RGB").save(image_bytes, format='PNG')
    image_bytes.seek(0)

    result = cloudinary.uploader.upload(
        image_bytes,
        public_id=f"centanet_{index}",
        overwrite=True
    )
    return result["secure_url"]

@app.route("/")
def home():
    return "✅ Centanet Rent Scraper is running."

@app.route("/run")
def run_scraper():
    try:
        # --- Setup Chrome Driver ---
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        # options.add_argument("--headless")  # turn on for deployment

        driver = webdriver.Chrome(service=Service(which("chromedriver")), options=options)
        driver.get("https://hk.centanet.com/findproperty/list/rent")

        # ✅ Step 1: Click the dropdown trigger
        dropdown_trigger = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        dropdown_trigger.click()
        print("✅ Clicked dropdown trigger")

        # ✅ Step 2: Wait for dropdown menu (dynamic)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dropdown-content-mobile"))
        )
        print("✅ Dropdown menu appeared")

        time.sleep(1)
        items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in items:
            text = item.text.strip()
            if "最新放盤" in text:
                driver.execute_script("arguments[0].click();", item)
                print("✅ Clicked 最新放盤")
                break
        else:
            print("❌ 最新放盤 not found")

        # ✅ Scroll to load all listings
        scroll_pause = 0.25
        scroll_y = 500
        current_y = 0
        max_y = driver.execute_script("return document.body.scrollHeight")

        while current_y < max_y:
            driver.execute_script(f"window.scrollTo(0, {current_y});")
            time.sleep(scroll_pause)
            current_y += scroll_y
            max_y = driver.execute_script("return document.body.scrollHeight")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list img"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")
        results = []

        for idx, card in enumerate(listings):
            try:
                title = card.select_one("span.title-lg").get_text(strip=True)
                subtitle = card.select_one("span.title-sm").get_text(strip=True) if card.select_one("span.title-sm") else ""
                area = card.select_one("div.area").get_text(strip=True) if card.select_one("div.area") else ""
                usable_area = card.select_one("div.area-block.usable-area div.num > span.hidden-xs-only")
                usable_area = usable_area.get_text(strip=True).replace("呎", "").replace(",", "") if usable_area else ""
                construction_area = card.select_one("div.area-block.construction-area div.num > span.hidden-xs-only")
                construction_area = construction_area.get_text(strip=True).replace("呎", "").replace(",", "") if construction_area else ""
                rent_tag = card.select_one("span.price-info")
                rent = rent_tag.get_text(strip=True).replace(",", "").replace("$", "") if rent_tag else ""
                rent = f"${int(rent):,}" if rent else ""

                image_url = ""
                for tag in card.select("img"):
                    src = tag.get("src", "")
                    if ".jpg" in src and src.startswith("http"):
                        image_url = src.split("?")[0]
                        break

                if not image_url:
                    print(f"⛔ No image for listing #{idx}")
                    continue

                summary = f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎 \n租金: {rent}"
                pic_generated = generate_image_with_photo_overlay(summary, image_url, idx)

                results.append({
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
                results.append({
                    "title": "❌ Error",
                    "summary": str(e)
                })

        driver.quit()
        return jsonify({"listings": results})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
