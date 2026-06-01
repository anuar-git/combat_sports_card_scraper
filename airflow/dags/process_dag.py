"""Phase 2: Process DAG — Spark transforms + dbt. Triggered by scrape DAG."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

sys.path.insert(0, "/opt/airflow")

from quality.alerts import alert_on_failure


def _update_pipeline_metrics(**context) -> None:
    """Collate latest run results and write data/metrics/latest.json atomically."""
    runs_dir = Path("/opt/airflow/data/runs")
    metrics_dir = Path("/opt/airflow/data/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    source_metrics: dict[str, dict] = {}

    run_files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    seen_sources: set[str] = set()
    for run_file in run_files:
        data = json.loads(run_file.read_text())
        source = data["source"]
        if source in seen_sources:
            continue
        seen_sources.add(source)

        last_scrape = data.get("completed_at")
        records_written = data.get("records_written", 0)
        records_invalid = data.get("records_valid", 0) - records_written if data.get("records_valid") else 0
        has_errors = bool(data.get("errors"))

        lag_hours = 0.0
        if last_scrape:
            try:
                scraped_dt = datetime.fromisoformat(last_scrape.replace("Z", "+00:00"))
                lag_hours = (datetime.now(timezone.utc) - scraped_dt).total_seconds() / 3600
            except ValueError:
                pass

        if has_errors:
            status = "error"
        elif lag_hours > 24:
            status = "stale"
        elif lag_hours > 8 or (data.get("records_valid", 0) > 0 and records_invalid / max(data.get("records_valid", 1), 1) > 0.1):
            status = "degraded"
        else:
            status = "healthy"

        source_metrics[source] = {
            "last_successful_scrape": last_scrape,
            "last_run_records_written": records_written,
            "last_run_records_invalid": max(records_invalid, 0),
            "status": status,
            "lag_hours": round(lag_hours, 2),
        }

    overall = "healthy"
    statuses = [m["status"] for m in source_metrics.values()]
    if "error" in statuses:
        overall = "error"
    elif "stale" in statuses:
        overall = "stale"
    elif "degraded" in statuses:
        overall = "degraded"

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_metrics,
        "dbt": {
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "models_run": 0,
            "status": "healthy",
        },
        "pipeline": {
            "overall_status": overall,
            "total_records_in_fct_card_sales": 0,
            "fighters_with_coverage": 0,
        },
    }

    tmp = metrics_dir / "latest.json.tmp"
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    os.replace(tmp, metrics_dir / "latest.json")


default_args = {
    "owner": "anuarhage",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "on_failure_callback": alert_on_failure,
    "sla": timedelta(hours=3),
}

with DAG(
    dag_id="alt_cards_process",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["alt", "processing", "phase2"],
    default_args=default_args,
) as dag:

    spark_ingest = BashOperator(
        task_id="spark_ingest",
        bash_command="cd /opt/airflow && python -m spark.jobs.ingest_raw",
    )

    spark_normalise = BashOperator(
        task_id="spark_normalise",
        bash_command="cd /opt/airflow && python -m spark.jobs.normalise_prices",
    )

    spark_enrich = BashOperator(
        task_id="spark_enrich",
        bash_command="cd /opt/airflow && python -m spark.jobs.enrich_fighters",
    )

    spark_benchmarks = BashOperator(
        task_id="spark_benchmarks",
        bash_command="cd /opt/airflow && python -m spark.jobs.compute_benchmarks",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/dbt && dbt run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt && dbt test --profiles-dir .",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    dbt_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command="cd /opt/airflow/dbt && dbt source freshness --profiles-dir . || true",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    update_metrics = PythonOperator(
        task_id="update_pipeline_metrics",
        python_callable=_update_pipeline_metrics,
    )

    (
        spark_ingest
        >> spark_normalise
        >> spark_enrich
        >> spark_benchmarks
        >> dbt_run
        >> dbt_test
        >> dbt_source_freshness
        >> update_metrics
    )
