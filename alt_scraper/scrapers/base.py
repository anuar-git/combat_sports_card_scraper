import re
import time
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from dateutil import parser as dateutil_parser

from utils.logger import get_logger
from utils.retry import retry_with_backoff
from utils.user_agents import get_request_headers


class BaseScraper(ABC):
    source: str = ""

    def __init__(self):
        from dotenv import load_dotenv
        import os
        load_dotenv()

        self.delay = float(os.getenv("REQUEST_DELAY_SECONDS", "2.0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "4"))
        self.log = get_logger(self.source or self.__class__.__name__)

        self.session = requests.Session()
        self.session.headers.update(get_request_headers())

    @abstractmethod
    def scrape(self, query: str, max_pages: int) -> list:
        ...

    def _get(self, url: str, params: dict = None) -> requests.Response:
        @retry_with_backoff(max_attempts=self.max_retries)
        def _fetch():
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response

        time.sleep(self.delay)
        return _fetch()

    def _parse_price(self, raw: str) -> Decimal | None:
        if not raw:
            return None
        cleaned = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _parse_date(self, raw: str) -> date | None:
        if not raw:
            return None
        try:
            return dateutil_parser.parse(raw, fuzzy=True).date()
        except (ValueError, OverflowError):
            return None

    def _extract_grade(self, title: str) -> tuple[str | None, str | None, float | None]:
        """Returns (grade_str, grader, grade_numeric) parsed from a listing title."""
        if not title:
            return None, None, None

        grade_pattern = re.compile(
            r"\b(PSA|BGS|SGC|CGC)\s*(10|[1-9](?:\.\d)?)\b",
            re.IGNORECASE,
        )
        match = grade_pattern.search(title)
        if match:
            grader_raw = match.group(1).upper()
            grade_num_str = match.group(2)
            try:
                grade_numeric = float(grade_num_str)
            except ValueError:
                grade_numeric = None
            grade_str = f"{grader_raw} {grade_num_str}"
            return grade_str, grader_raw, grade_numeric

        if re.search(r"\braw\b", title, re.IGNORECASE):
            return "Raw", "Raw", None

        return None, None, None
