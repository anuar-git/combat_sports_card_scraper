"""Entry point: python -m pipeline.run_scrape --source ebay --query "UFC PSA" --max-pages 5"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv()

# Add project root to path when run as a module
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.card_sale import RawCardSale, ScrapeBatchResult
from utils.dedup import filter_new_records, load_seen_hashes, save_seen_hashes, update_seen_hashes
from utils.logger import get_logger

log = get_logger("pipeline")

SEEN_HASHES_PATH = os.getenv("SEEN_HASHES_PATH", "./data/seen_hashes.json")
RUNS_DIR = os.getenv("RUNS_DIR", "./data/runs")


def _output_path(source: str, run_id: str, output_dir: str) -> Path:
    now = datetime.now(timezone.utc)
    partition = Path(output_dir) / source / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"
    partition.mkdir(parents=True, exist_ok=True)
    filename = f"{source}_{now.strftime('%Y%m%d')}_{run_id[:8]}.ndjson"
    return partition / filename


def _write_records(records: list[RawCardSale], path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")


def _run_scraper(scraper, queries: list[str], max_pages: int, dry_run: bool, output_dir: str,
                 seen: set[str], run_id: str) -> ScrapeBatchResult:
    source = scraper.source
    started_at = datetime.now(timezone.utc)
    errors: list[str] = []
    total_scraped = 0
    total_valid = 0
    total_new = 0
    total_written = 0

    for query in queries:
        log.info("scraper_query_start", source=source, query=query)
        try:
            raw_records = scraper.scrape(query, max_pages)
        except Exception as exc:
            msg = f"Scrape error for query '{query}': {exc}"
            log.error("scraper_error", source=source, error=msg)
            errors.append(msg)
            continue

        total_scraped += len(raw_records)

        valid_records: list[RawCardSale] = []
        for record in raw_records:
            if isinstance(record, RawCardSale):
                valid_records.append(record)
                continue
            try:
                valid_records.append(RawCardSale.model_validate(record))
            except ValidationError as exc:
                errors.append(f"Validation error: {exc}")

        total_valid += len(valid_records)

        new_records = filter_new_records(valid_records, seen)
        total_new += len(new_records)

        if not dry_run and new_records:
            out_path = _output_path(source, run_id, output_dir)
            _write_records(new_records, out_path)
            total_written += len(new_records)
            log.info("records_written", path=str(out_path), count=len(new_records))

        seen = update_seen_hashes(new_records, seen)

    return ScrapeBatchResult(
        source=source,
        run_id=run_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        records_scraped=total_scraped,
        records_valid=total_valid,
        records_new=total_new,
        records_written=total_written,
        errors=errors,
    ), seen


def main():
    parser = argparse.ArgumentParser(description="Combat sports card scraper")
    parser.add_argument("--source", default="all", choices=["ebay", "pwcc", "myslabs", "all"])
    parser.add_argument("--query", default=None, help="Override default queries")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", default=os.getenv("RAW_DATA_DIR", "./data/raw"))
    args = parser.parse_args()

    log.info("pipeline_start", source=args.source, dry_run=args.dry_run)

    seen = load_seen_hashes(SEEN_HASHES_PATH)
    log.info("dedup_loaded", count=len(seen))

    from scrapers.ebay import EbayScraper, EBAY_QUERIES
    from scrapers.pwcc import PwccScraper, PWCC_QUERIES
    from scrapers.myslabs import MySlabsScraper, MYSLABS_QUERIES

    scraper_configs = {
        "ebay": (EbayScraper, EBAY_QUERIES),
        "pwcc": (PwccScraper, PWCC_QUERIES),
        "myslabs": (MySlabsScraper, MYSLABS_QUERIES),
    }

    sources_to_run = list(scraper_configs.keys()) if args.source == "all" else [args.source]
    run_results = []
    import uuid
    run_id = str(uuid.uuid4())

    for source_name in sources_to_run:
        ScraperClass, default_queries = scraper_configs[source_name]
        queries = [args.query] if args.query else default_queries

        scraper = ScraperClass()
        result, seen = _run_scraper(
            scraper, queries, args.max_pages, args.dry_run, args.output_dir, seen, run_id
        )
        run_results.append(result)
        log.info(
            "scraper_complete",
            source=source_name,
            scraped=result.records_scraped,
            valid=result.records_valid,
            new=result.records_new,
            written=result.records_written,
            errors=len(result.errors),
        )

    if not args.dry_run:
        save_seen_hashes(seen, SEEN_HASHES_PATH)
        log.info("dedup_saved", count=len(seen))

        runs_dir = Path(RUNS_DIR)
        runs_dir.mkdir(parents=True, exist_ok=True)
        for result in run_results:
            run_path = runs_dir / f"{result.run_id}.json"
            run_path.write_text(result.model_dump_json(indent=2))
            log.info("run_result_written", path=str(run_path))

    log.info("pipeline_complete", runs=len(run_results))


if __name__ == "__main__":
    main()
