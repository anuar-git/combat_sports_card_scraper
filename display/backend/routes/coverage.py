import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.responses import PipelineStatus

router = APIRouter()

# Resolve the metrics file relative to the repo root, not this file's location.
_METRICS_FILE = Path(os.getenv("METRICS_FILE", "data/metrics/latest.json"))


@router.get("", response_model=PipelineStatus)
def get_coverage():
    # Support both absolute and relative paths; relative paths are from cwd.
    path = _METRICS_FILE if _METRICS_FILE.is_absolute() else Path.cwd() / _METRICS_FILE
    if not path.exists():
        raise HTTPException(status_code=503, detail="Pipeline metrics not available")
    try:
        return PipelineStatus.model_validate(json.loads(path.read_text()))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Invalid metrics file: {exc}") from exc
