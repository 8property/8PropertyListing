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
        driver = webdriver.Chrome(service=Service(which("chromedriver")), options=options)

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

        # ✅ Click dropdown trigger using JS
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        driver.execute_script("arguments[0].click();", dropdown_trigger)
        print("✅ Clicked dropdown trigger")

        # ✅ Wait for dropdown options to show
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dropdown-content-mobile"))
        )
        time.sleep(0.5)

        # ✅ Click on 最新放盤
        dropdown_items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in dropdown_items:
            text = item.text.strip()
            if "最新放盤" in text:
                driver.execute_script("arguments[0].click();", item)
                print("✅ Clicked 最新放盤")
                time.sleep(0.5)
                break

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        results = []
        for idx, card in enumerate(listings[:15]):
            try:
                title = card.select_one("span.title-lg")
                subtitle = card.select_one("span.title-sm")
                area = card.select_one("div.area")
                usable_tag = card.select_one("div.area-block.usable-area div.num > span.hidden-xs-only")
                construction_tag = card.select_one("div.area-block.construction-area div.num > span.hidden-xs-only")
                rent_tag = card.select_one("span.price-info")

                rent = rent_tag.get_text(strip=True).replace(",", "").replace("$", "") if rent_tag else ""
                rent = f"{int(rent):,}" if rent.isdigit() else rent

                image_url = ""
                for img_tag in card.select("img"):
                    src = img_tag.get("src", "")
                    if ".jpg" in src and src.startswith("http"):
                        image_url = src.split("?")[0]
                        break

                results.append({
                    "title": title.text.strip() if title else "",
                    "subtitle": subtitle.text.strip() if subtitle else "",
                    "area": area.text.strip() if area else "",
                    "usable_area": usable_tag.text.strip().replace("呎", "") if usable_tag else "",
                    "construction_area": construction_tag.text.strip().replace("呎", "") if construction_tag else "",
                    "rent": f"${rent}" if rent else "",
                    "image_url": image_url
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
