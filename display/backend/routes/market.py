from google.cloud import bigquery
from fastapi import APIRouter, Query

from db.client import get_bq_client
from db.queries import MARKET_OVERVIEW_QUERY, FIGHTER_SEARCH_QUERY
from cache import cached
from models.responses import MarketOverviewItem, Fighter

router = APIRouter()


def _row_to_overview(row) -> dict:
    return {
        "fighter_id": row["fighter_id"],
        "fighter_name": row["fighter_name_canonical"],
        "sport": row["sport"],
        "grade_label": row["grade_label"],
        "vwap_7d": float(row["vwap_7d"]) if row["vwap_7d"] is not None else None,
        "vwap_30d": float(row["vwap_30d"]) if row["vwap_30d"] is not None else None,
        "sale_count_30d": int(row["sale_count_30d"]),
        "price_pct_change_7d": float(row["price_pct_change_7d"]) if row["price_pct_change_7d"] is not None else None,
        "price_pct_change_30d": float(row["price_pct_change_30d"]) if row["price_pct_change_30d"] is not None else None,
    }


@cached(key_fn=lambda: "market_overview")
def _fetch_overview() -> list[dict]:
    client = get_bq_client()
    rows = client.query(MARKET_OVERVIEW_QUERY).result()
    return [_row_to_overview(r) for r in rows]


@router.get("/overview", response_model=list[MarketOverviewItem])
def get_market_overview():
    return _fetch_overview()


@router.get("/search", response_model=list[Fighter])
def search_fighters(q: str = Query(..., min_length=1, max_length=100)):
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{q}%"),
        ]
    )
    rows = client.query(FIGHTER_SEARCH_QUERY, job_config=job_config).result()
    return [
        {
            "fighter_id": r["fighter_id"],
            "fighter_name": r["fighter_name_canonical"],
            "sport": r["sport"],
            "promotion": r["promotion"],
            "vwap_30d": float(r["vwap_30d"]) if r["vwap_30d"] is not None else None,
        }
        for r in rows
    ]
