import os
import random
import re
import stat
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

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

# PWCC was acquired by Fanatics; sales history now lives at this subdomain
_BASE_URL = "https://sales-history.fanaticscollect.com/"

# CSS selector for sale item links — stable because path segments (/buy-now/, /weekly-auction/,
# /premier/) are product URL conventions, not generated class names
_SALE_LINK_CSS = (
    "a[href*='fanaticscollect.com/buy-now/'],"
    "a[href*='fanaticscollect.com/weekly-auction/'],"
    "a[href*='fanaticscollect.com/premier/']"
)

_SALE_TYPE_MAP = {
    "buy now": "buy_it_now",
    "auction": "auction",
    "weekly auction": "auction",
    "premier auction": "auction",
    "premier": "auction",
}

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

        driver_path = ChromeDriverManager().install()
        # webdriver_manager bug: returns THIRD_PARTY_NOTICES (executable) instead of the
        # actual binary (non-executable). Always resolve to the real binary by name.
        driver_path = os.path.join(os.path.dirname(driver_path), "chromedriver")
        if not os.access(driver_path, os.X_OK):
            os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        driver.implicitly_wait(5)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def _extract_listing(self, link_el) -> RawCardSale | None:
        try:
            listing_url = link_el.get_attribute("href") or ""
            if not listing_url:
                return None

            # UUID is the last path segment
            listing_id = listing_url.rstrip("/").split("/")[-1]

            # Card container is the direct parent of the sale link
            card = link_el.find_element(By.XPATH, "..")

            # Image — stable alt attribute
            try:
                image_url = card.find_element(By.CSS_SELECTOR, "img[alt='Card image']").get_attribute("src")
            except NoSuchElementException:
                image_url = None

            # All text paragraphs within the card
            paras = [p.text.strip() for p in card.find_elements(By.CSS_SELECTOR, "p.chakra-text") if p.text.strip()]

            # Title: first paragraph that isn't a price or sold-date line
            title = next(
                (p for p in paras if not p.startswith("$") and not p.startswith("Sold on")),
                "",
            )
            if not title:
                return None

            # Price: paragraph starting with "$"
            price_raw = next((p for p in paras if p.startswith("$")), "")
            price = self._parse_price(price_raw)
            if price is None:
                return None

            # "Sold on May 31, 2026 in Buy Now"
            sold_text = next((p for p in paras if p.startswith("Sold on")), "")
            m = re.match(r"Sold on (.+?) in (.+)", sold_text)
            sale_date = self._parse_date(m.group(1)) if m else None
            sale_date = sale_date or datetime.now(timezone.utc).date()

            sale_type_raw = m.group(2).lower() if m else ""
            sale_type = next(
                (v for k, v in _SALE_TYPE_MAP.items() if k in sale_type_raw),
                "buy_it_now",
            )

            grade_str, grader, grade_numeric = self._extract_grade(title)

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
                sale_type=sale_type,
            )
        except Exception as exc:
            self.log.warning("fanatics_record_error", error=str(exc))
            return None

    def _dismiss_consent_banner(self, driver: webdriver.Chrome) -> None:
        try:
            banner = driver.find_element(By.CSS_SELECTOR, "aside.dg-consent-banner")
            driver.execute_script("arguments[0].remove();", banner)
        except NoSuchElementException:
            pass

    def _click_see_more(self, driver: webdriver.Chrome) -> bool:
        self._dismiss_consent_banner(driver)
        try:
            btn = driver.find_element(By.XPATH, "//button[normalize-space()='See more']")
            driver.execute_script("arguments[0].click();", btn)
            return True
        except NoSuchElementException:
            return False

    def scrape(self, query: str, max_pages: int = 10) -> list[RawCardSale]:
        self.log.info("fanatics_scrape_start", query=query, max_pages=max_pages)
        records: list[RawCardSale] = []
        seen_ids: set[str] = set()
        driver = self._build_driver()

        try:
            url = f"{_BASE_URL}?query={quote_plus(query)}"
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, _SALE_LINK_CSS))
                )
            except TimeoutException:
                self.log.warning("fanatics_no_results", query=query)
                return records

            for load in range(max_pages):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)

                link_els = driver.find_elements(By.CSS_SELECTOR, _SALE_LINK_CSS)
                batch = []
                for link_el in link_els:
                    href = link_el.get_attribute("href") or ""
                    item_id = href.rstrip("/").split("/")[-1]
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    record = self._extract_listing(link_el)
                    if record:
                        batch.append(record)

                records.extend(batch)
                self.log.info("fanatics_batch", load=load + 1, new=len(batch), total=len(records))

                if load + 1 < max_pages:
                    if not self._click_see_more(driver):
                        self.log.info("fanatics_no_more_pages")
                        break
                    time.sleep(self.delay + random.uniform(0.5, 1.5))

        except WebDriverException as exc:
            self.log.error("fanatics_driver_error", error=str(exc))
        finally:
            driver.quit()

        self.log.info("fanatics_scrape_complete", total=len(records))
        return records
