# Combat Sports Card Intelligence — Phase 1 Scraping Layer

Production-grade data acquisition pipeline for combat sports trading card sale records. Ingests closed listings from eBay (Browse API with HTML fallback) and PWCC Marketplace (Selenium), validates every record against a strict Pydantic schema, deduplicates across runs, and writes Hive-partitioned NDJSON ready for Phase 2 PySpark ingestion.

## Prerequisites

- Python 3.11+
- Google Chrome (required for PWCC Selenium scraper)
- An eBay Developer account with Browse API access (optional — HTML fallback activates automatically without credentials)

## Setup

```bash
# Clone and enter directory
cd alt_scraper

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env and fill in your EBAY_APP_ID and EBAY_CERT_ID
```

## Running a scrape

```bash
# Scrape eBay with default queries
python -m pipeline.run_scrape --source ebay

# Scrape PWCC with default queries
python -m pipeline.run_scrape --source pwcc

# Both sources
python -m pipeline.run_scrape --source all

# Custom query, limited pages, dry run (validates but does not write)
python -m pipeline.run_scrape --source ebay --query "UFC Khabib PSA 10" --max-pages 3 --dry-run

# Custom output directory
python -m pipeline.run_scrape --source ebay --output-dir /mnt/data/raw
```

## Running tests

```bash
pytest tests/ -v
```

## Output format

Records are written as newline-delimited JSON (`.ndjson`), one record per line, with Hive-style path partitioning:

```
data/raw/{source}/year={YYYY}/month={MM}/day={DD}/{source}_{YYYYMMDD}_{run_id[:8]}.ndjson
```

Example:
```
data/raw/ebay/year=2025/month=06/day=14/ebay_20250614_a3f9c12b.ndjson
```

Each run produces a summary at `data/runs/{run_id}.json` with counts of scraped / valid / new / written records and any non-fatal errors.

The deduplication store at `data/seen_hashes.json` persists SHA-256 hashes across runs so no listing is written twice.

## Data sources

| Source | Method | Notes |
|--------|--------|-------|
| eBay | Browse API (OAuth 2.0 app token) | Falls back to HTML scraping if API returns 403 or credentials absent |
| PWCC Marketplace | Selenium + ChromeDriver | Requires Chrome; `SELENIUM_HEADLESS=true` by default |

## Known limitations

- **PWCC DOM selectors** in `scrapers/pwcc.py:SELECTORS` may drift if PWCC redesigns their marketplace. Update the selector constants when this happens.
- **eBay API rate limits**: the Browse API allows ~5,000 calls/day on the basic tier. The `REQUEST_DELAY_SECONDS` env var controls inter-request throttling.
- **Non-USD listings**: eBay items priced in non-USD currencies are skipped by the API scraper.
- **PWCC completed sales filter**: the `status=sold` query parameter may not be honoured if PWCC changes their URL scheme.
