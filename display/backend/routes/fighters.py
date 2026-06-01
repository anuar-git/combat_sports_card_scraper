from google.cloud import bigquery
from fastapi import APIRouter, HTTPException

from db.client import get_bq_client
from db.queries import (
    FIGHTER_METADATA_QUERY,
    FIGHTER_PRICE_HISTORY_QUERY,
    RECENT_SALES_QUERY,
    ALL_FIGHTERS_QUERY,
)
from cache import cached
from models.responses import Fighter, FighterPriceHistory, PricePoint, RecentSale

router = APIRouter()


def _fighter_params(fighter_id: str) -> bigquery.QueryJobConfig:
    return bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fighter_id", "STRING", fighter_id),
        ]
    )


@cached(key_fn=lambda fighter_id: f"fighter_{fighter_id}")
def _fetch_fighter(fighter_id: str) -> dict | None:
    client = get_bq_client()
    cfg = _fighter_params(fighter_id)

    meta_rows = list(client.query(FIGHTER_METADATA_QUERY, job_config=cfg).result())
    if not meta_rows:
        return None
    meta = meta_rows[0]

    history_rows = list(client.query(FIGHTER_PRICE_HISTORY_QUERY, job_config=cfg).result())
    sales_rows = list(client.query(RECENT_SALES_QUERY, job_config=cfg).result())

    return {
        "fighter_id": meta["fighter_id"],
        "fighter_name": meta["fighter_name_canonical"],
        "sport": meta["sport"],
        "promotion": meta["promotion"],
        "price_history": [
            {
                "date": r["benchmark_date"],
                "grade_label": r["grade_label"],
                "vwap_7d": float(r["vwap_7d"]) if r["vwap_7d"] is not None else None,
                "vwap_30d": float(r["vwap_30d"]) if r["vwap_30d"] is not None else None,
                "sale_count": int(r["sale_count_30d"]),
            }
            for r in history_rows
        ],
        "recent_sales": [
            {
                "listing_title": r["listing_title"],
                "sale_price_usd": float(r["sale_price_usd"]),
                "sale_date": r["sale_date"],
                "sale_type": r["sale_type"],
                "source": r["source"],
                "listing_url": r["listing_url"],
                "grade_label": r["grade_label"],
            }
            for r in sales_rows
        ],
    }


@cached(key_fn=lambda: "all_fighters")
def _fetch_all_fighters() -> list[dict]:
    client = get_bq_client()
    rows = client.query(ALL_FIGHTERS_QUERY).result()
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


@router.get("", response_model=list[Fighter])
def list_fighters():
    return _fetch_all_fighters()


@router.get("/{fighter_id}", response_model=FighterPriceHistory)
def get_fighter(fighter_id: str):
    data = _fetch_fighter(fighter_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return data
