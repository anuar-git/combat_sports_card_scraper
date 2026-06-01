"""dbt source freshness checker and data quality helpers."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


class DataFreshnessError(Exception):
    pass


def run_dbt_freshness_check(dbt_dir: str | None = None, profiles_dir: str | None = None) -> dict[str, str]:
    """
    Run `dbt source freshness` and return mapping of source_name -> status.
    Raises DataFreshnessError if any source is in 'error' state.
    """
    project_dir = dbt_dir or os.getenv("DBT_PROJECT_DIR", "./dbt")
    profiles = profiles_dir or project_dir

    result = subprocess.run(
        ["dbt", "source", "freshness", "--output", "json", "--profiles-dir", profiles],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    sources_json = Path(project_dir) / "target" / "sources.json"
    if not sources_json.exists():
        raise DataFreshnessError(f"dbt freshness output not found at {sources_json}")

    data = json.loads(sources_json.read_text())

    statuses: dict[str, str] = {}
    error_sources: list[str] = []

    for result_node in data.get("results", []):
        source_name = result_node.get("unique_id", "unknown")
        status = result_node.get("status", "unknown")
        statuses[source_name] = status
        if status == "error":
            error_sources.append(source_name)

    if error_sources:
        raise DataFreshnessError(f"Stale sources detected: {', '.join(error_sources)}")

    return statuses


def validate_scrape_outputs(runs_dir: str = "./data/runs") -> dict[str, int]:
    """
    Read ScrapeBatchResult JSONs and return records_written per source.
    Raises ValueError if any source wrote 0 records in the most recent run.
    """
    runs_path = Path(runs_dir)
    if not runs_path.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_dir}")

    run_files = sorted(runs_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_files:
        raise ValueError("No run result files found in runs directory")

    records_by_source: dict[str, int] = {}
    # Only look at the most recent run_id batch (files share a run_id prefix in UUID)
    for run_file in run_files:
        data = json.loads(run_file.read_text())
        source = data.get("source", "unknown")
        written = data.get("records_written", 0)
        if source not in records_by_source:
            records_by_source[source] = written

        # Stop after we've seen one file per source (most recent)
        if len(records_by_source) >= 2:
            break

    zero_sources = [s for s, n in records_by_source.items() if n == 0]
    if zero_sources:
        raise ValueError(f"Zero records written for sources: {', '.join(zero_sources)}")

    return records_by_source
