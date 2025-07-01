from flask import Flask, jsonify
import os
import time
from bs4 import BeautifulSoup
import undetected_chromedriver as uc  # edited!!
from selenium.webdriver.chrome.options import Options  # edited!!
from selenium.webdriver.chrome.service import Service  # ✅ ADD this near top

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "✅ Centanet Flask app is running. Visit /scrape to run the scraper."

    @app.route("/scrape", methods=["GET"])
    def scrape_centanet():
        try:
            # === 1. Set up undetected Chrome driver ===
            options = Options()  # edited!!
            options.binary_location = "/usr/bin/google-chrome"  # edited!!
            options.add_argument("--headless")  # edited!!
            options.add_argument("--no-sandbox")  # edited!!
            options.add_argument("--disable-gpu")  # edited!!
            options.add_argument("--disable-dev-shm-usage")  # edited!!
            options.add_argument("--window-size=1920,1080")  # edited!!


            service = Service("/usr/bin/chromedriver")  # ✅ CHROME DRIVER PATH ON RENDER
            driver = uc.Chrome(service=service, options=options)  # ✅ FIXED
            
            base_url = "https://hk.centanet.com/findproperty/list/rent"
            driver.get(base_url)
            time.sleep(3)

            all_data = []

            for page in range(1):  # currently scrape only 1 page
                scroll_pause_time = 0.25
                scroll_increment = 500
                max_scroll = driver.execute_script("return document.body.scrollHeight")
                current_position = 0

                while current_position < max_scroll:
                    driver.execute_script(f"window.scrollTo(0, {current_position});")
                    time.sleep(scroll_pause_time)
                    current_position += scroll_increment
                    max_scroll = driver.execute_script("return document.body.scrollHeight")

                time.sleep(0.5)
                soup = BeautifulSoup(driver.page_source, "html.parser")

                listings = soup.select("div.list")
                for card in listings[:5]:  # limit to 5 listings for performance  # edited!!
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

                        rent = card.select_one("span.price-info")
                        rent = rent.text.strip().replace(",", "").replace("$", "") if rent else ""

                        image_tag = card.select_one("img")
                        image_url = image_tag.get("src") if image_tag else ""

                        output = f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎\n租金: ${int(rent):,}" if rent.isdigit() else ""

                        all_data.append({
                            "development": title,
                            "details": subtitle,
                            "area": area,
                            "usable_area": usable_area,
                            "construction_area": construction_area,
                            "rent": rent,
                            "image_url": image_url,
                            "output": output
                        })
                    except:
                        continue

                driver.execute_script("window.scrollTo(0, 0);")
                try:
                    next_btn = driver.find_element("css selector", "button.btn-next")
                    if "disabled" in next_btn.get_attribute("class"):
                        break
                    next_btn.click()
                    time.sleep(3)
                except:
                    break

            driver.quit()
            return jsonify({"listings": all_data})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
