from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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
        options.add_argument("--headless")  # Use headless for cloud deployment
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        driver = webdriver.Chrome(service=Service(which("chromedriver")), options=options)

        driver.get("https://hk.centanet.com/findproperty/list/rent")

        # ✅ Step 1a: Remove overlay if blocking
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.deepLink-main"))
            )
            driver.execute_script("arguments[0].remove();", overlay)
            print("🧹 Removed blocking overlay")
        except:
            print("ℹ️ No overlay found")

        # ✅ Step 1b: Click the dropdown using JS
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        driver.execute_script("arguments[0].click();", dropdown_trigger)
        print("✅ Clicked dropdown trigger")

        # ✅ Step 2: Wait for dropdown content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dropdown-content-mobile"))
        )
        print("✅ Dropdown content loaded")

        time.sleep(1)  # Ensure content has loaded fully

        # ✅ Step 3: Find and click '最新放盤'
        dropdown_items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for i in range(len(dropdown_items)):
            item = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")[i]
            text = item.text.strip()
            print(f"📌 Option: {text}")
            if "最新放盤" in text:
                driver.execute_script("arguments[0].click();", item)
                print("✅ Clicked 最新放盤")
                break
        else:
            print("❌ 最新放盤 not found")

        # ✅ Wait for updated listings
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list"))
        )

        # ✅ Step 4: Scrape listings
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        results = []
        for card in listings[:5]:
            title = card.select_one("span.title-lg")
            subtitle = card.select_one("span.title-sm")
            area = card.select_one("div.area")
            rent = card.select_one("span.price-info")

            results.append({
                "title": title.text.strip() if title else "",
                "subtitle": subtitle.text.strip() if subtitle else "",
                "area": area.text.strip() if area else "",
                "rent": rent.text.strip() if rent else ""
            })

        driver.quit()
        return jsonify({"listings": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
