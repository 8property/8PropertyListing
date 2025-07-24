from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import time
from shutil import which

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Centanet scraper is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    try:
        # === Setup Chrome ===
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless")  # Keep headless for Render
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        driver = webdriver.Chrome(service=Service(which("chromedriver")), options=options)

        driver.get("https://hk.centanet.com/findproperty/list/rent")

        # ✅ Step 1a: Remove any overlay
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.deepLink-main"))
            )
            driver.execute_script("arguments[0].remove();", overlay)
            print("🧹 Removed blocking overlay")
        except:
            print("ℹ️ No overlay found")

        # ✅ Step 1b: Click dropdown menu
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        driver.execute_script("arguments[0].click();", dropdown_trigger)
        print("✅ Clicked dropdown trigger")

        # ✅ Step 2: Wait for dropdown content to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dropdown-content-mobile"))
        )
        print("✅ Dropdown content loaded")
        time.sleep(0.5)

        # ✅ Step 3: Find and click "最新放盤"
        dropdown_items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in dropdown_items:
            text = item.text.strip()
            print(f"📌 Option: {text}")
            if "最新放盤" in text:
                driver.execute_script("arguments[0].click();", item)
                print("✅ Clicked 最新放盤")
                time.sleep(0.5)
                break
        else:
            print("❌ 最新放盤 not found")

        # ✅ Step 4: Wait for listings to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list"))
        )

        # ✅ Step 5: Scrape listings
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        results = []
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
                rent = f"${int(rent):,}" if rent else ""
                image_tags = card.select("img")
    
                # Loop through and pick the first .jpg image
                image_url = ""
                for tag in image_tags:
                    src = tag.get("src", "")
                    if ".jpg" in src and src.startswith("http"):
                        image_url = src.split("?")[0].strip()
                        break
    
                # ✅ Skip this listing if no valid image found
                if not image_url:
                    print(f"⛔ Skipped listing #{idx} due to missing image URL")
                    continue
    
                summary = f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎 \n租金: {rent}"
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
                print(f"⚠️ Error parsing card {idx}: {e}")

        driver.quit()
        return jsonify({"listings": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
