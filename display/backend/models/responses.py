from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class MarketOverviewItem(BaseModel):
    fighter_id: str
    fighter_name: str
    sport: str
    grade_label: str
    vwap_7d: float | None
    vwap_30d: float | None
    sale_count_30d: int
    price_pct_change_7d: float | None
    price_pct_change_30d: float | None


class Fighter(BaseModel):
    fighter_id: str
    fighter_name: str
    sport: str
    promotion: str | None
    vwap_30d: float | None


class PricePoint(BaseModel):
    date: date
    grade_label: str
    vwap_7d: float | None
    vwap_30d: float | None
    sale_count: int


class RecentSale(BaseModel):
    listing_title: str
    sale_price_usd: float
    sale_date: date
    sale_type: str
    source: str
    listing_url: str | None
    grade_label: str


class FighterPriceHistory(BaseModel):
    fighter_id: str
    fighter_name: str
    sport: str
    promotion: str | None
    price_history: list[PricePoint]
    recent_sales: list[RecentSale]


class Mover(BaseModel):
    fighter_id: str
    fighter_name: str
    grade_label: str
    vwap_7d: float | None
    vwap_30d: float | None
    price_pct_change_7d: float
    sale_count_7d: int


# Coverage / pipeline status (mirrors monitoring/api/models.py shape)
class SourceStatus(BaseModel):
    last_successful_scrape: datetime | None
    last_run_records_written: int
    last_run_records_invalid: int
    status: Literal["healthy", "degraded", "stale", "error"]
    lag_hours: float


class DbtStatus(BaseModel):
    last_run_at: datetime | None
    tests_passed: int
    tests_failed: int
    models_run: int
    status: Literal["healthy", "degraded", "stale", "error"]


class PipelineSummary(BaseModel):
    overall_status: Literal["healthy", "degraded", "stale", "error"]
    total_records_in_fct_card_sales: int
    fighters_with_coverage: int


class PipelineStatus(BaseModel):
    updated_at: datetime
    sources: dict[str, SourceStatus]
    dbt: DbtStatus
    pipeline: PipelineSummary
