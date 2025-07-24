from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time, os, requests
from PIL import Image, ImageDraw, ImageFont
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
if not os.path.exists(font_path):
    raise FileNotFoundError("Font file not found.")
font = ImageFont.truetype(font_path, 48)

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

# === Flask App ===
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Centanet scraper is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    driver = None
    try:
        # === Setup Chrome ===
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        driver = webdriver.Chrome(options=options)
        driver.get("https://hk.centanet.com/findproperty/list/rent")

        # ✅ Remove overlay if it exists
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.deepLink-main"))
            )
            driver.execute_script("arguments[0].remove();", overlay)
            print("🧹 Removed blocking overlay")
        except:
            print("ℹ️ No overlay found")

        # ✅ Click dropdown & select 最新放盤
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        driver.execute_script("arguments[0].click();", dropdown_trigger)
        print("✅ Clicked dropdown trigger")
        time.sleep(0.5)

        dropdown_items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in dropdown_items:
            if "最新放盤" in item.text.strip():
                driver.execute_script("arguments[0].click();", item)
                print("✅ Clicked 最新放盤")
                time.sleep(3)
                break

        # ✅ Scroll until at least 15 listings are loaded
        # Scroll & wait until at least 15 listings with image src are loaded
        max_scrolls = 20
        scroll_pause = 1.5

        for i in range(max_scrolls):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(scroll_pause)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            listings = soup.select("div.list")
            valid_images = [
                card.select_one("img.el-image__inner") or card.select_one("img")
                for card in listings if (card.select_one("img.el-image__inner") or card.select_one("img"))
            ]
            print(f"📷 Listings: {len(listings)}, with image: {len(valid_images)}")

            if len(valid_images) >= 15:
                break

        # ✅ Final parsing
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        results = []
        for idx, card in enumerate(listings[:15]):
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
                rent = f"${int(rent):,}" if rent else ""

                image_url = ""
                img_tag = card.select_one("div.img-wrap img") or card.select_one("img")
                if img_tag:
                    try:
                        src = img_tag.get("data-src") or img_tag.get("src", "")
                        if ".jpg" in src and src.startswith("http"):
                            image_url = src.split("?")[0].strip()
                    except Exception as e:
                        print(f"⚠️ Failed to extract image src in listing #{idx}: {e}")
                else:
                    print(f"⛔ No <img> tag found in listing #{idx}")
                    
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
            except Exception as parse_err:
                print(f"⚠️ Error parsing card {idx}: {parse_err}")

        return jsonify({"listings": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
