from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Centanet Rent Scraper is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    try:
        # === Setup headless Chrome ===
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
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

        for card in listings:
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

                listings_data.append({
                    "title": title,
                    "subtitle": subtitle,
                    "area": area,
                    "usable_area": usable_area,
                    "construction_area": construction_area,
                    "rent": rent,
                    "image_url": image_url,
                    "summary": summary
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
