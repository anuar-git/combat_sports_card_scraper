"""
PSA cert enrichment utility.

PSA's public API (api.psacard.com) exposes cert details — grade, player name, year,
set, and population — but NOT sale prices. This module is therefore an enrichment
utility, not a sales scraper. It:

  1. Extracts PSA cert numbers from listing title strings.
  2. Looks them up via the public API (100 calls/day quota).
  3. Caches all results locally so the quota is not wasted on re-lookups.

Usage (standalone):
    python -m pipeline.run_psa_enrich

Usage (programmatic):
    from scrapers.psa import PsaCertEnricher
    enricher = PsaCertEnricher()
    data = enricher.lookup_cert("12345678")
"""

import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from utils.logger import get_logger

_API_URL = "https://api.psacard.com/publicapi/cert/GetByCertNumber/{cert}"
_CERT_RE = re.compile(
    r"""
    (?:
        \bcert(?:ificate)?\s*[:#]?\s*   # "cert #", "certificate:", etc.
        |PSA\s*cert\s*[:#]?\s*
    )
    ([0-9]{6,9})                        # 6–9 digit cert number
    |
    (?<!\d)([0-9]{8})(?!\d)             # bare 8-digit number (less reliable)
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DEFAULT_CACHE = Path("data/psa_certs.json")
_DAILY_QUOTA = 100


class PsaCertEnricher:
    def __init__(self, cache_path: Path = _DEFAULT_CACHE):
        self.log = get_logger("psa")
        self.cache_path = cache_path
        self._cache: dict = self._load_cache()
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; CombatCardBot/1.0)",
        })
        # Track calls made this calendar day to respect the 100/day quota
        self._today = date.today().isoformat()
        self._calls_today: int = self._cache.get("_meta", {}).get("calls_today", {}).get(self._today, 0)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cache(self) -> dict:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        meta = self._cache.setdefault("_meta", {})
        meta.setdefault("calls_today", {})[self._today] = self._calls_today
        self.cache_path.write_text(json.dumps(self._cache, indent=2, default=str))

    # ------------------------------------------------------------------
    # Cert number extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_cert_numbers(title: str) -> list[str]:
        """Return all PSA cert numbers found in a listing title."""
        results = []
        for m in _CERT_RE.finditer(title):
            cert = m.group(1) or m.group(2)
            if cert:
                results.append(cert.lstrip("0") or "0")
        return list(dict.fromkeys(results))  # deduplicate, preserve order

    # ------------------------------------------------------------------
    # API lookup
    # ------------------------------------------------------------------

    def lookup_cert(self, cert_number: str) -> dict | None:
        """
        Return PSA cert details for the given cert number.

        Returns cached data if available. Returns None if the quota is
        exhausted, the cert doesn't exist, or the API errors.
        """
        key = str(cert_number).lstrip("0") or "0"

        if key in self._cache:
            return self._cache[key]

        if self._calls_today >= _DAILY_QUOTA:
            self.log.warning("psa_quota_exhausted", calls=self._calls_today, cert=key)
            return None

        url = _API_URL.format(cert=key)
        try:
            resp = self._session.get(url, timeout=15)
            self._calls_today += 1

            if resp.status_code == 404:
                self.log.info("psa_cert_not_found", cert=key)
                self._cache[key] = None
                self._save_cache()
                return None

            if resp.status_code == 429:
                self.log.warning("psa_rate_limited", cert=key)
                self._calls_today = _DAILY_QUOTA  # stop trying for today
                return None

            resp.raise_for_status()
            payload = resp.json()

            # Normalise the nested PSACard object if present
            cert_obj = payload.get("PSACert") or payload
            result = {
                "cert_number": key,
                "grade": cert_obj.get("GradeDescription"),
                "grade_numeric": _parse_grade_numeric(cert_obj.get("GradeDescription")),
                "grader": "PSA",
                "year": cert_obj.get("Year"),
                "brand": cert_obj.get("Brand"),
                "subject": cert_obj.get("Subject"),
                "variety": cert_obj.get("Variety"),
                "spec_level": cert_obj.get("SpecLevel"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            self._cache[key] = result
            self._save_cache()
            self.log.info("psa_cert_fetched", cert=key, subject=result["subject"])
            time.sleep(0.5)  # polite pause between calls
            return result

        except requests.RequestException as exc:
            self.log.error("psa_api_error", cert=key, error=str(exc))
            return None

    # ------------------------------------------------------------------
    # Batch enrichment
    # ------------------------------------------------------------------

    def enrich_records(self, titles: list[str]) -> dict[str, dict]:
        """
        Given a list of listing titles, extract all cert numbers, look them
        up, and return a mapping of cert_number → cert_data.
        """
        all_certs: list[str] = []
        for title in titles:
            all_certs.extend(self.extract_cert_numbers(title))

        unique = list(dict.fromkeys(all_certs))
        results = {}
        for cert in unique:
            data = self.lookup_cert(cert)
            if data:
                results[cert] = data

        self.log.info("psa_enrichment_complete", certs_found=len(unique), enriched=len(results))
        return results


def _parse_grade_numeric(grade_desc: str | None) -> float | None:
    if not grade_desc:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", grade_desc)
    return float(m.group(1)) if m else None
