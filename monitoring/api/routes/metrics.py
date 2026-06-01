"""Per-source metrics and run history endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from monitoring.api.models import RunHistoryEntry, SourceStatus

router = APIRouter()

METRICS_PATH = Path(os.getenv("METRICS_PATH", "./data/metrics/latest.json"))
RUNS_DIR = Path(os.getenv("RUNS_DIR", "./data/runs"))


def _load_metrics() -> dict:
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="Metrics file not found")
    return json.loads(METRICS_PATH.read_text())


@router.get("/{source}", response_model=SourceStatus)
def source_metrics(source: str):
    data = _load_metrics()
    sources = data.get("sources", {})
    if source not in sources:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    return SourceStatus.model_validate(sources[source])


@router.get("/history/runs", response_model=list[RunHistoryEntry])
def run_history():
    if not RUNS_DIR.exists():
        return []

    run_files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    results: list[RunHistoryEntry] = []
    for run_file in run_files:
        try:
            data = json.loads(run_file.read_text())
            results.append(RunHistoryEntry.model_validate(data))
        except Exception:
            continue

    return results
