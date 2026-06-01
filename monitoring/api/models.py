"""Pydantic response models for the monitoring API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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


class RunHistoryEntry(BaseModel):
    source: str
    run_id: str
    started_at: datetime
    completed_at: datetime
    records_scraped: int
    records_valid: int
    records_new: int
    records_written: int
    errors: list[str]
