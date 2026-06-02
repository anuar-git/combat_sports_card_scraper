"""
PSA cert enrichment runner.

Scans all collected NDJSON records, extracts PSA cert numbers from listing
titles, looks them up via the PSA public API (100 calls/day quota), and
saves results to data/psa_certs.json for use by the Spark enrich job.

Usage:
    python -m pipeline.run_psa_enrich
    python -m pipeline.run_psa_enrich --raw-dir data/raw --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.psa import PsaCertEnricher
from utils.logger import get_logger

log = get_logger("psa_enrich")

RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "data/raw")
PSA_CACHE_PATH = Path(os.getenv("PSA_CACHE_PATH", "data/psa_certs.json"))


def _iter_titles(raw_dir: str):
    """Yield listing_title strings from all NDJSON files under raw_dir."""
    for ndjson in Path(raw_dir).rglob("*.ndjson"):
        try:
            with open(ndjson) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        title = record.get("listing_title", "")
                        if title:
                            yield title
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def main():
    parser = argparse.ArgumentParser(description="PSA cert enrichment runner")
    parser.add_argument("--raw-dir", default=RAW_DATA_DIR)
    parser.add_argument("--cache-path", default=str(PSA_CACHE_PATH))
    parser.add_argument("--dry-run", action="store_true", help="Extract cert numbers only, skip API calls")
    args = parser.parse_args()

    enricher = PsaCertEnricher(cache_path=Path(args.cache_path))

    titles = list(_iter_titles(args.raw_dir))
    log.info("psa_enrich_start", titles_scanned=len(titles))

    # Collect all cert numbers across all titles
    all_certs: list[str] = []
    for title in titles:
        all_certs.extend(enricher.extract_cert_numbers(title))

    unique_certs = list(dict.fromkeys(all_certs))
    already_cached = sum(1 for c in unique_certs if c in enricher._cache)
    to_fetch = [c for c in unique_certs if c not in enricher._cache]

    log.info(
        "psa_certs_found",
        total=len(unique_certs),
        cached=already_cached,
        to_fetch=len(to_fetch),
    )

    if args.dry_run:
        log.info("psa_dry_run", cert_numbers=unique_certs[:20])
        return

    enriched = 0
    for cert in to_fetch:
        result = enricher.lookup_cert(cert)
        if result:
            enriched += 1
        if enricher._calls_today >= 100:
            log.warning("psa_quota_reached", enriched=enriched, remaining=len(to_fetch) - enriched)
            break

    log.info("psa_enrich_complete", enriched=enriched, cache_size=len(enricher._cache))


if __name__ == "__main__":
    main()
