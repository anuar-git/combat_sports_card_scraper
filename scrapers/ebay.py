import base64
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from models.card_sale import RawCardSale
from scrapers.base import BaseScraper
from utils.user_agents import get_request_headers

EBAY_QUERIES = [
    "UFC trading card PSA graded",
    "UFC rookie card BGS",
    "MMA trading card Conor McGregor",
    "Bellator MMA trading card",
    "UFC Topps card graded",
    "UFC Panini card PSA 10",
    "ONE Championship trading card",
    "boxing trading card PSA graded",
]

_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
_SEARCH_URL = "https://www.ebay.com/sch/i.html"
_SPORTS_CARD_CATEGORY = "183050"


class EbayScraper(BaseScraper):
    source = "ebay"

    def __init__(self):
        super().__init__()
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self.app_id = os.getenv("EBAY_APP_ID", "")
        self.cert_id = os.getenv("EBAY_CERT_ID", "")

    def _get_access_token(self) -> str | None:
        if not self.app_id or not self.cert_id:
            self.log.warning("ebay_no_credentials", msg="EBAY_APP_ID/EBAY_CERT_ID not set")
            return None

        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        credentials = base64.b64encode(f"{self.app_id}:{self.cert_id}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            resp = requests.post(_TOKEN_URL, headers=headers, data=data, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            self._access_token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 7200))
            from datetime import timedelta
            self._token_expiry = now + timedelta(seconds=expires_in - 60)
            self.log.info("ebay_token_fetched", expires_in=expires_in)
            return self._access_token
        except Exception as exc:
            self.log.error("ebay_token_error", error=str(exc))
            return None

    def _scrape_api(self, query: str, max_pages: int) -> list[dict]:
        token = self._get_access_token()
        if not token:
            raise ValueError("No eBay access token available")

        records = []
        offset = 0
        limit = 200

        for page in range(max_pages):
            params = {
                "q": query,
                "category_ids": _SPORTS_CARD_CATEGORY,
                "filter": "conditionIds:{1000|1500|2000|2500|3000},buyingOptions:{AUCTION|FIXED_PRICE}",
                "sort": "endTimeSoonest",
                "limit": limit,
                "offset": offset,
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            }

            try:
                resp = self.session.get(_BROWSE_URL, params=params, headers=headers, timeout=30)
                resp.raise_for_status()
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 403:
                    self.log.warning("ebay_api_403", page=page)
                    raise
                raise

            data = resp.json()
            items = data.get("itemSummaries", [])
            if not items:
                self.log.info("ebay_api_no_more_items", page=page, offset=offset)
                break

            records.extend(items)
            self.log.info("ebay_api_page_fetched", page=page + 1, count=len(items))

            if len(items) < limit:
                break
            offset += limit
            time.sleep(self.delay)

        return records

    def _parse_api_record(self, item: dict) -> RawCardSale | None:
        try:
            price_raw = item.get("price", {})
            currency = price_raw.get("currency", "USD")
            if currency != "USD":
                return None

            price = self._parse_price(price_raw.get("value", ""))
            if price is None:
                return None

            sale_date = self._parse_date(item.get("itemEndDate", ""))
            if sale_date is None:
                sale_date = datetime.now(timezone.utc).date()

            title = item.get("title", "")
            grade_str, grader, grade_numeric = self._extract_grade(title)

            buying_options = item.get("buyingOptions", [])
            if "AUCTION" in buying_options:
                sale_type = "auction"
            else:
                sale_type = "buy_it_now"

            listing_url = item.get("itemWebUrl", "")
            image_url = item.get("image", {}).get("imageUrl")

            return RawCardSale(
                listing_id=item["itemId"],
                source="ebay",
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
            self.log.warning("ebay_parse_error", error=str(exc), item_id=item.get("itemId"))
            return None

    def _scrape_html(self, query: str, max_pages: int) -> list[RawCardSale]:
        self.log.info("ebay_html_fallback", query=query)
        records = []

        for page in range(1, max_pages + 1):
            params = {
                "_nkw": query,
                "_pgn": page,
                "LH_Sold": "1",
                "LH_Complete": "1",
            }
            try:
                resp = self._get(_SEARCH_URL, params=params)
            except Exception as exc:
                self.log.error("ebay_html_fetch_error", page=page, error=str(exc))
                break

            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select("li.s-item")
            if not items:
                break

            for item in items:
                record = self._parse_html_item(item)
                if record:
                    records.append(record)

            self.log.info("ebay_html_page", page=page, items=len(items))
            time.sleep(self.delay)

        return records

    def _parse_html_item(self, item) -> RawCardSale | None:
        try:
            title_el = item.select_one("div.s-item__title span")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or title.lower() == "shop on ebay":
                return None

            price_el = item.select_one("span.s-item__price")
            price_raw = price_el.get_text(strip=True) if price_el else ""
            price = self._parse_price(price_raw)
            if price is None:
                return None

            url_el = item.select_one("a.s-item__link")
            listing_url = url_el["href"] if url_el and url_el.has_attr("href") else None
            if not listing_url:
                return None

            listing_id = listing_url.split("/itm/")[-1].split("?")[0] if "/itm/" in listing_url else listing_url[-20:]

            date_el = item.select_one("span.s-item__ended-date")
            date_raw = date_el.get_text(strip=True) if date_el else ""
            sale_date = self._parse_date(date_raw) or datetime.now(timezone.utc).date()

            img_el = item.select_one("img.s-item__image-img")
            image_url = img_el.get("src") if img_el else None

            grade_str, grader, grade_numeric = self._extract_grade(title)

            return RawCardSale(
                listing_id=listing_id,
                source="ebay",
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
            self.log.warning("ebay_html_parse_error", error=str(exc))
            return None

    def scrape(self, query: str, max_pages: int = 10) -> list[RawCardSale]:
        self.log.info("ebay_scrape_start", query=query, max_pages=max_pages)

        try:
            api_items = self._scrape_api(query, max_pages)
            records = [r for item in api_items if (r := self._parse_api_record(item)) is not None]
            self.log.info("ebay_api_complete", records=len(records))
            return records
        except Exception as exc:
            self.log.warning("ebay_api_failed_falling_back", error=str(exc))
            return self._scrape_html(query, max_pages)
