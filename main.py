from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask app is running."

@app.route("/run", methods=["GET"])
def run_scraper():
    try:
        url = "https://hk.centanet.com/findproperty/rent"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select("div.card")
        listings = []

        for card in cards:
            title_tag = card.select_one("span.title-lg")
            if not title_tag:
                continue  # skip if title not found

            title = title_tag.get_text(strip=True)
            subtitle = card.select_one("div.subtitle").get_text(strip=True) if card.select_one("div.subtitle") else ""
            rent = card.select_one("div.price span.value").get_text(strip=True) if card.select_one("div.price span.value") else ""
            area = card.select_one("span.district").get_text(strip=True) if card.select_one("span.district") else ""
            usable_area = card.select_one("div.area-block.usable-area span.hidden-xs-only")
            usable_area = usable_area.get_text(strip=True).replace("呎", "") if usable_area else ""

            construction_area = card.select_one("div.area-block.construction-area span.hidden-xs-only")
            construction_area = construction_area.get_text(strip=True).replace("呎", "") if construction_area else ""

            image_tag = card.select_one("img")
            image_url = image_tag["src"] if image_tag and image_tag.get("src", "").startswith("http") else ""

            summary = f"{title}\n{subtitle}\n{area} | 實用: {usable_area} 呎 建築: {construction_area} 呎\n租金: ${rent}"

            listings.append({
                "title": title,
                "subtitle": subtitle,
                "rent": rent,
                "area": area,
                "usable_area": usable_area,
                "construction_area": construction_area,
                "image_url": image_url,
                "summary": summary
            })

        return jsonify({"listings": listings})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)