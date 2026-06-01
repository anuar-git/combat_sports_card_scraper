from fastapi import APIRouter, Query
from typing import Literal

from db.client import get_bq_client
from db.queries import TOP_MOVERS_QUERY
from cache import cached
from models.responses import Mover

router = APIRouter()


@cached(key_fn=lambda: "top_movers")
def _fetch_movers() -> list[dict]:
    client = get_bq_client()
    rows = client.query(TOP_MOVERS_QUERY).result()
    return [
        {
            "fighter_id": r["fighter_id"],
            "fighter_name": r["fighter_name_canonical"],
            "grade_label": r["grade_label"],
            "vwap_7d": float(r["vwap_7d"]) if r["vwap_7d"] is not None else None,
            "vwap_30d": float(r["vwap_30d"]) if r["vwap_30d"] is not None else None,
            "price_pct_change_7d": float(r["price_pct_change_7d"]),
            "sale_count_7d": int(r["sale_count_7d"]),
        }
        for r in rows
    ]


@router.get("", response_model=list[Mover])
def get_movers(
    direction: Literal["up", "down", "both"] = Query("both"),
    limit: int = Query(10, ge=1, le=20),
):
    all_movers = _fetch_movers()

    if direction == "up":
        filtered = [m for m in all_movers if m["price_pct_change_7d"] > 0]
        filtered.sort(key=lambda m: m["price_pct_change_7d"], reverse=True)
    elif direction == "down":
        filtered = [m for m in all_movers if m["price_pct_change_7d"] < 0]
        filtered.sort(key=lambda m: m["price_pct_change_7d"])
    else:
        filtered = sorted(all_movers, key=lambda m: abs(m["price_pct_change_7d"]), reverse=True)

    return filtered[:limit]
