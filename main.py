from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from shutil import which
import os
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Centanet Scraper is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    try:
        # === Setup headless Chrome ===
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{int(time.time())}")

        driver = webdriver.Chrome(service=Service(which("chromedriver")), options=options)
        driver.get("https://hk.centanet.com/findproperty/list/rent")

        # ✅ Click dropdown
        dropdown_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".title-sort-switch.hidden-xs-only .left .el-dropdown-link"))
        )
        dropdown_trigger.click()

        # ✅ Wait for dropdown to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dropdown-content-mobile"))
        )

        # ✅ Select '最新放盤'
        items = driver.find_elements(By.CSS_SELECTOR, "div.dropdown-content-mobile li")
        for item in items:
            if "最新放盤" in item.text.strip():
                driver.execute_script("arguments[0].click();", item)
                break

        # ✅ Scroll to load data
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # ✅ Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        data = []
        for listing in listings:
            title = listing.select_one("span.title-lg")
            subtitle = listing.select_one("span.title-sm")
            area = listing.select_one("div.area")
            rent_tag = listing.select_one("span.price-info")

            rent = rent_tag.get_text(strip=True).replace(",", "").replace("$", "") if rent_tag else ""
            rent = f"{int(rent):,}" if rent.isdigit() else rent

            data.append({
                "title": title.get_text(strip=True) if title else "N/A",
                "subtitle": subtitle.get_text(strip=True) if subtitle else "N/A",
                "area": area.get_text(strip=True) if area else "N/A",
                "rent": rent or "N/A"
            })

        driver.quit()
        return jsonify({"listings": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
