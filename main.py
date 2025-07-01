#!/usr/bin/env python3
"""
Centanet Property Scraper
A standalone script to scrape Hong Kong rental property data from Centanet
Optimized for cloud deployment on Render
"""

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging
import argparse
import sys

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_chrome_driver():
    """Setup Chrome WebDriver with options optimized for cloud deployment"""
    options = Options()

    # Essential options for cloud deployment
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logger.info("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
        raise


def scroll_page(driver):
    """Scroll through the page to load all content"""
    try:
        scroll_pause_time = 0.5
        scroll_increment = 500
        max_scroll = driver.execute_script("return document.body.scrollHeight")
        current_position = 0

        logger.debug("Starting page scroll to load dynamic content")

        while current_position < max_scroll:
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(scroll_pause_time)
            current_position += scroll_increment
            max_scroll = driver.execute_script(
                "return document.body.scrollHeight")

        # Scroll back to top
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        logger.debug("Page scrolling completed")

    except Exception as e:
        logger.error(f"Error during scrolling: {str(e)}")


def extract_property_data(card):
    """Extract data from a single property card"""
    try:
        # Title (required field)
        title_tag = card.select_one("span.title-lg")
        if not title_tag or not title_tag.text.strip():
            return None

        title = title_tag.text.strip()

        # Subtitle/details
        subtitle_tag = card.select_one("span.title-sm")
        subtitle = subtitle_tag.text.strip() if subtitle_tag else ""

        # Area information
        area_tag = card.select_one("div.area")
        area = area_tag.text.strip() if area_tag else ""

        # Usable area
        usable_tag = card.select_one(
            "div.area-block.usable-area div.num > span.hidden-xs-only")
        usable_area = ""
        if usable_tag:
            usable_area = usable_tag.get_text(strip=True).replace("呎",
                                                                  "").replace(
                                                                      ",", "")

        # Construction area
        construction_tag = card.select_one(
            "div.area-block.construction-area div.num > span.hidden-xs-only")
        construction_area = ""
        if construction_tag:
            construction_area = construction_tag.get_text(strip=True).replace(
                "呎", "").replace(",", "")

        # Rent price
        rent_tag = card.select_one("span.price-info")
        rent_value = ""
        if rent_tag:
            rent_value = rent_tag.text.strip().replace(",",
                                                       "").replace("$", "")

        # Image URL
        image_tag = card.select_one("img")
        image_url = image_tag.get("src") if image_tag else ""

        # Create formatted output
        output = ""
        if rent_value and rent_value.isdigit():
            output = f"{title}\n{subtitle}\n{area} | 實用: {usable_area}呎\n租金: ${int(rent_value):,}"

        return {
            "development": title,
            "details": subtitle,
            "area": area,
            "usable_area": usable_area,
            "construction_area": construction_area,
            "rent": rent_value,
            "image_url": image_url,
            "output": output
        }

    except Exception as e:
        logger.debug(f"Error extracting property data: {str(e)}")
        return None


def extract_page_data(driver):
    """Extract property data from current page"""
    page_data = []

    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.list")

        logger.info(f"Found {len(listings)} property listings on current page")

        for card in listings:
            try:
                property_data = extract_property_data(card)
                if property_data:
                    page_data.append(property_data)
            except Exception as e:
                logger.debug(
                    f"Skipped property due to extraction error: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error extracting page data: {str(e)}")

    return page_data


def go_to_next_page(driver):
    """Navigate to the next page"""
    try:
        # Look for next button
        next_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-next")))

        # Check if button is disabled
        btn_class = next_btn.get_attribute("class") or ""
        if "disabled" in btn_class:
            logger.info("Next button is disabled, no more pages available")
            return False

        # Click next button
        next_btn.click()
        logger.info("Clicked next page button")

        # Wait for page to load
        time.sleep(3)

        # Wait for new content to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list")))

        return True

    except Exception as e:
        logger.error(f"Error navigating to next page: {str(e)}")
        return False


def scrape_centanet_properties(pages=1):
    """Main scraping function"""
    base_url = "https://hk.centanet.com/findproperty/list/rent"
    all_data = []

    # Setup driver
    driver = setup_chrome_driver()

    try:
        logger.info(f"Starting scraping process for {pages} page(s)")
        logger.info(f"Navigating to {base_url}")

        driver.get(base_url)

        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list")))
        logger.info("Page loaded successfully")

        for page_num in range(pages):
            logger.info(f"Processing page {page_num + 1} of {pages}")

            # Scroll to load all content
            scroll_page(driver)

            # Extract data from current page
            page_data = extract_page_data(driver)
            all_data.extend(page_data)

            logger.info(
                f"Extracted {len(page_data)} properties from page {page_num + 1}"
            )

            # Navigate to next page if not the last page
            if page_num < pages - 1:
                if not go_to_next_page(driver):
                    logger.warning("Could not navigate to next page, stopping")
                    break

    except Exception as e:
        logger.error(f"Scraping error: {str(e)}")
        raise

    finally:
        try:
            driver.quit()
            logger.info("Chrome WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {str(e)}")

    logger.info(
        f"Scraping completed successfully. Total properties: {len(all_data)}")
    return all_data


def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(
        description='Scrape Centanet property data')
    parser.add_argument('--pages',
                        type=int,
                        default=1,
                        help='Number of pages to scrape (1-10, default: 1)')
    parser.add_argument(
        '--output',
        type=str,
        default='centanet_properties.xlsx',
        help='Output filename (default: centanet_properties.xlsx)')
    parser.add_argument('--format',
                        choices=['excel', 'csv', 'json'],
                        default='excel',
                        help='Output format (default: excel)')

    args = parser.parse_args()

    # Validate pages parameter
    if args.pages < 1 or args.pages > 10:
        logger.error("Pages must be between 1 and 10")
        sys.exit(1)

    try:
        logger.info(f"Starting Centanet property scraper")
        logger.info(f"Target pages: {args.pages}")
        logger.info(f"Output file: {args.output}")
        logger.info(f"Output format: {args.format}")

        properties = scrape_centanet_properties(pages=args.pages)

        if not properties:
            logger.warning("No properties were scraped")
            sys.exit(0)

        # Create DataFrame
        df = pd.DataFrame(properties)

        # Save to file based on format
        if args.format == 'excel':
            df.to_excel(args.output, index=False)
        elif args.format == 'csv':
            df.to_csv(args.output, index=False)
        elif args.format == 'json':
            df.to_json(args.output, orient='records', indent=2)

        logger.info(
            f"✅ Successfully saved {len(properties)} properties to {args.output}"
        )

        # Print summary
        print(f"\n📊 SCRAPING SUMMARY")
        print(f"=" * 50)
        print(f"Properties found: {len(properties)}")
        print(f"Pages scraped: {args.pages}")
        print(f"Output file: {args.output}")
        print(f"Format: {args.format}")
        print(f"=" * 50)

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
