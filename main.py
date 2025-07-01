from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import os
import time

app = Flask(__name__)

@app.route("/scrape", methods=["GET"])
def scrape_centanet():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920x1080")

        driver = webdriver.Chrome(options=options)
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

                    construction_tag = card.select_one("div.area-block.construction-ar
