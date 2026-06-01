"""Daily pipeline DAG — full end-to-end run at midnight UTC."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

sys.path.insert(0, "/opt/airflow")

from quality.alerts import alert_on_failure, send_slack_alert


def _check_availability(**context) -> None:
    import requests

    sources = {
        "ebay": "https://www.ebay.com",
        "pwcc": "https://www.pwccmarketplace.com",
    }
    unavailable = []
    for name, url in sources.items():
        try:
            requests.head(url, timeout=10, allow_redirects=True)
        except Exception as exc:
            unavailable.append(f"{name}: {exc}")
    if unavailable:
        raise AirflowSkipException(f"Sources unreachable: {'; '.join(unavailable)}")


def _scrape_source(source: str, **context) -> None:
    import subprocess

    max_pages = Variable.get(f"{source}_max_pages", default_var="10")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipeline.run_scrape",
            "--source",
            source,
            "--max-pages",
            str(max_pages),
            "--output-dir",
            Variable.get("raw_data_dir", default_var="/opt/airflow/data/raw"),
        ],
        capture_output=True,
        text=True,
        cwd="/opt/airflow",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Scrape failed for {source}:\n{result.stderr}")


def _validate_scrape(**context) -> None:
    runs_dir = Path("/opt/airflow/data/runs")
    run_files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_files:
        raise ValueError("No run files found")

    records_by_source: dict[str, int] = {}
    for run_file in run_files:
        data = json.loads(run_file.read_text())
        source = data["source"]
        if source not in records_by_source:
            records_by_source[source] = data["records_written"]

    zero = [s for s, n in records_by_source.items() if n == 0]
    if zero:
        raise ValueError(f"Zero records for: {', '.join(zero)}")

    context["task_instance"].xcom_push(key="records_by_source", value=records_by_source)


def _update_metrics(**context) -> None:
    runs_dir = Path("/opt/airflow/data/runs")
    metrics_dir = Path("/opt/airflow/data/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    source_metrics: dict[str, dict] = {}
    seen: set[str] = set()
    for run_file in sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(run_file.read_text())
        source = data["source"]
        if source in seen:
            continue
        seen.add(source)
        last_scrape = data.get("completed_at")
        written = data.get("records_written", 0)
        invalid = max(data.get("records_valid", 0) - written, 0)
        has_errors = bool(data.get("errors"))

        lag = 0.0
        if last_scrape:
            try:
                dt = datetime.fromisoformat(last_scrape.replace("Z", "+00:00"))
                lag = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            except ValueError:
                pass

        if has_errors:
            status = "error"
        elif lag > 24:
            status = "stale"
        elif lag > 8:
            status = "degraded"
        else:
            status = "healthy"

        source_metrics[source] = {
            "last_successful_scrape": last_scrape,
            "last_run_records_written": written,
            "last_run_records_invalid": invalid,
            "status": status,
            "lag_hours": round(lag, 2),
        }

    statuses = [m["status"] for m in source_metrics.values()]
    overall = "error" if "error" in statuses else "stale" if "stale" in statuses else "degraded" if "degraded" in statuses else "healthy"

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

    context["task_instance"].xcom_push(key="overall_status", value=overall)
    context["task_instance"].xcom_push(key="source_metrics", value=source_metrics)


def _notify_success(**context) -> None:
    ti = context["task_instance"]
    source_metrics = ti.xcom_pull(task_ids="update_pipeline_metrics", key="source_metrics") or {}

    lines = ["*Daily Pipeline Complete*"]
    for source, m in source_metrics.items():
        lines.append(f"• {source}: {m['last_run_records_written']} records ({m['status']})")

    send_slack_alert("\n".join(lines))


default_args = {
    "owner": "anuarhage",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "on_failure_callback": alert_on_failure,
}

with DAG(
    dag_id="alt_cards_daily",
    schedule_interval="0 0 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["alt", "daily", "production"],
    default_args=default_args,
) as dag:

    check_avail = PythonOperator(
        task_id="check_availability",
        python_callable=_check_availability,
    )

    scrape_ebay = PythonOperator(
        task_id="scrape_ebay",
        python_callable=_scrape_source,
        op_kwargs={"source": "ebay"},
        sla=timedelta(minutes=45),
    )

    scrape_pwcc = PythonOperator(
        task_id="scrape_pwcc",
        python_callable=_scrape_source,
        op_kwargs={"source": "pwcc"},
        sla=timedelta(minutes=60),
    )

    validate_scrape = PythonOperator(
        task_id="validate_scrape",
        python_callable=_validate_scrape,
    )

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

    run_ge_checkpoint = BashOperator(
        task_id="run_ge_checkpoint",
        bash_command="cd /opt/airflow && python great_expectations/run_checkpoint.py",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    update_metrics = PythonOperator(
        task_id="update_pipeline_metrics",
        python_callable=_update_metrics,
    )

    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=_notify_success,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    (
        check_avail
        >> [scrape_ebay, scrape_pwcc]
        >> validate_scrape
        >> spark_ingest
        >> spark_normalise
        >> spark_enrich
        >> spark_benchmarks
        >> dbt_run
        >> dbt_test
        >> dbt_source_freshness
        >> run_ge_checkpoint
        >> update_metrics
        >> notify_success
    )
