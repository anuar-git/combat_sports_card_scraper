import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from models.card_sale import RawCardSale
from scrapers.base import BaseScraper

_BASE_URL = "https://www.myslabs.com"
_ARCHIVE_URL = f"{_BASE_URL}/browse/archive/"

MYSLABS_QUERIES = [
    "UFC PSA",
    "UFC BGS",
    "MMA graded card",
    "boxing PSA graded",
    "Conor McGregor card",
    "Jon Jones card",
]


class MySlabsScraper(BaseScraper):
    source = "myslabs"

    def __init__(self):
        super().__init__()
        # requests has no built-in brotli support; advertising 'br' in Accept-Encoding
        # causes MySlabs to return brotli-compressed bytes that can't be decoded.
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def _parse_card(self, card) -> RawCardSale | None:
        try:
            link_el = card.select_one("a[href^='/slab/view/']")
            if not link_el:
                return None
            listing_url = _BASE_URL + link_el["href"]
            listing_id = link_el["href"].strip("/").split("/")[-1]

            title_el = card.select_one("div.slab-title")
            # Fall back to img alt if slab-title is empty
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                img = card.select_one("img[alt]")
                title = img["alt"].strip() if img else ""
            if not title:
                return None

            price_el = card.select_one("div.item-price")
            if not price_el:
                return None
            # Strip the tooltip icon text, keep only the price string
            price_text = price_el.find(string=True, recursive=False)
            if price_text:
                price_text = price_text.strip()
            else:
                price_text = price_el.get_text(separator=" ", strip=True).split()[0]
            price = self._parse_price(price_text)
            if price is None:
                return None

            date_el = card.select_one("div.slab-details small")
            sale_date = self._parse_date(date_el.get_text(strip=True)) if date_el else None
            sale_date = sale_date or datetime.now(timezone.utc).date()

            img_el = card.select_one("img[data-src]")
            image_url = img_el["data-src"] if img_el else None
            if not image_url:
                img_el = card.select_one("img[src]")
                image_url = img_el["src"] if img_el else None

            # MySlabs shows a sale-type icon image — detect auction vs fixed-price
            type_img = card.select_one("img[src*='fixed-price'], img[src*='auction']")
            if type_img and "auction" in (type_img.get("src") or ""):
                sale_type = "auction"
            else:
                sale_type = "buy_it_now"

            grade_str, grader, grade_numeric = self._extract_grade(title)

            return RawCardSale(
                listing_id=listing_id,
                source="myslabs",
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
            self.log.warning("myslabs_parse_error", error=str(exc))
            return None

    def scrape(self, query: str, max_pages: int = 10) -> list[RawCardSale]:
        self.log.info("myslabs_scrape_start", query=query, max_pages=max_pages)
        records: list[RawCardSale] = []

        for page in range(1, max_pages + 1):
            params = {"q": query, "page": page}
            try:
                resp = self._get(_ARCHIVE_URL, params=params)
            except Exception as exc:
                self.log.error("myslabs_fetch_error", page=page, error=str(exc))
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("div.slab_item")
            if not cards:
                self.log.info("myslabs_no_more_results", page=page)
                break

            page_records = []
            for card in cards:
                record = self._parse_card(card)
                if record:
                    page_records.append(record)

            records.extend(page_records)
            self.log.info("myslabs_page", page=page, count=len(page_records))

            # Stop early if last page returned fewer cards than a full page
            if len(cards) < 24:
                break

            time.sleep(self.delay)

        self.log.info("myslabs_scrape_complete", total=len(records))
        return records
