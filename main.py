    from flask import Flask, jsonify
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import time
    import os

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "✅ Flask app is running."

    @app.route("/run", methods=["GET"])
    def run_scraper():
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920x1080")

            driver = webdriver.Chrome(options=options)
            driver.get("https://hk.centanet.com/findproperty/租")
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.quit()

            # === Extracting Sample Titles and Links (Example)
            cards = soup.select("div.list-card-right")
            results = []

            for card in cards[:5]:  # Limit to 5 for demo
                title = card.select_one("span.title-lg")
                rent = card.select_one("div.price-lg")
                subtitle = card.select_one("div.subtitle")
                if title:
                    results.append({
                        "title": title.get_text(strip=True),
                        "rent": rent.get_text(strip=True) if rent else "",
                        "subtitle": subtitle.get_text(strip=True) if subtitle else ""
                    })

            return jsonify({"status": "success", "data": results})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    # ✅ This makes it work on Render
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
