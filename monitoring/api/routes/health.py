"""Health and pipeline status endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from monitoring.api.models import PipelineStatus

router = APIRouter()

METRICS_PATH = Path(os.getenv("METRICS_PATH", "./data/metrics/latest.json"))


def _load_metrics() -> dict:
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="Metrics file not found — pipeline has not run yet")
    return json.loads(METRICS_PATH.read_text())


@router.get("/health")
def liveness() -> dict:
    return {"status": "ok"}


@router.get("/status", response_model=PipelineStatus)
def pipeline_status():
    data = _load_metrics()
    status = PipelineStatus.model_validate(data)
    overall = data.get("pipeline", {}).get("overall_status", "error")
    http_status = 200 if overall in ("healthy", "degraded") else 503
    return JSONResponse(content=json.loads(status.model_dump_json()), status_code=http_status)
