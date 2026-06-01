import random
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from models.card_sale import RawCardSale
from scrapers.base import BaseScraper
from utils.user_agents import get_random_user_agent

SELECTORS = {
    "listing_card": "div.lot-card",
    "title": "h3.lot-card__title",
    "price": "span.lot-card__price",
    "sale_date": "span.lot-card__date",
    "listing_url": "a.lot-card__link",
    "image": "img.lot-card__image",
}

_BASE_URL = "https://www.pwccmarketplace.com/market/search"

PWCC_QUERIES = [
    "UFC PSA",
    "MMA card graded",
    "boxing card PSA",
    "UFC BGS",
]


class PwccScraper(BaseScraper):
    source = "pwcc"

    def __init__(self):
        super().__init__()
        import os
        self.headless = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
        self._driver: webdriver.Chrome | None = None

    def _build_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(f"user-agent={get_random_user_agent()}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
        driver.implicitly_wait(5)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def _scroll_to_bottom(self, driver: webdriver.Chrome) -> None:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

    def _extract_listing(self, card, driver: webdriver.Chrome) -> RawCardSale | None:
        try:
            title_el = card.find_element(By.CSS_SELECTOR, SELECTORS["title"])
            title = title_el.text.strip()
        except NoSuchElementException:
            title = ""

        if not title:
            return None

        try:
            price_el = card.find_element(By.CSS_SELECTOR, SELECTORS["price"])
            price = self._parse_price(price_el.text.strip())
        except NoSuchElementException:
            price = None

        if price is None:
            return None

        try:
            date_el = card.find_element(By.CSS_SELECTOR, SELECTORS["sale_date"])
            sale_date = self._parse_date(date_el.text.strip())
        except NoSuchElementException:
            sale_date = None
        sale_date = sale_date or datetime.now(timezone.utc).date()

        try:
            link_el = card.find_element(By.CSS_SELECTOR, SELECTORS["listing_url"])
            listing_url = link_el.get_attribute("href") or ""
        except NoSuchElementException:
            listing_url = ""

        if not listing_url:
            return None

        listing_id = listing_url.rstrip("/").split("/")[-1]

        try:
            img_el = card.find_element(By.CSS_SELECTOR, SELECTORS["image"])
            image_url = img_el.get_attribute("src")
        except NoSuchElementException:
            image_url = None

        grade_str, grader, grade_numeric = self._extract_grade(title)

        try:
            return RawCardSale(
                listing_id=listing_id,
                source="pwcc",
                scraped_at=datetime.now(timezone.utc),
                sale_price_usd=price,
                sale_date=sale_date,
                listing_title=title,
                grade=grade_str,
                grader=grader,
                grade_numeric=grade_numeric,
                listing_url=listing_url,
                image_url=image_url,
                sale_type="auction",
            )
        except Exception as exc:
            self.log.warning("pwcc_record_validation_error", error=str(exc))
            return None

    def scrape(self, query: str, max_pages: int = 10) -> list[RawCardSale]:
        self.log.info("pwcc_scrape_start", query=query, max_pages=max_pages)
        records: list[RawCardSale] = []
        driver = self._build_driver()

        try:
            for page in range(1, max_pages + 1):
                url = f"{_BASE_URL}?keywords={query}&status=sold&page={page}"
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["listing_card"]))
                    )
                except TimeoutException:
                    self.log.info("pwcc_no_listings_on_page", page=page)
                    break

                self._scroll_to_bottom(driver)

                cards = driver.find_elements(By.CSS_SELECTOR, SELECTORS["listing_card"])
                if not cards:
                    self.log.info("pwcc_empty_page", page=page)
                    break

                page_records = []
                for card in cards:
                    record = self._extract_listing(card, driver)
                    if record:
                        page_records.append(record)

                records.extend(page_records)
                self.log.info("pwcc_page_scraped", page=page, count=len(page_records))

                sleep_time = self.delay + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)

        except WebDriverException as exc:
            self.log.error("pwcc_driver_error", error=str(exc))
        finally:
            driver.quit()

        self.log.info("pwcc_scrape_complete", total=len(records))
        return records
