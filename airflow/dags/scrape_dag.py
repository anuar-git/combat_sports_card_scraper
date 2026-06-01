"""Phase 1: Scrape DAG — runs every 6 hours, triggers process DAG on success."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

sys.path.insert(0, "/opt/airflow")

from quality.alerts import alert_on_failure


def _check_source_availability(**context) -> None:
    import requests

    sources = {
        "ebay": "https://www.ebay.com",
        "pwcc": "https://www.pwccmarketplace.com",
    }
    unavailable = []
    for name, url in sources.items():
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            context["task_instance"].xcom_push(key=f"{name}_response_ms", value=resp.elapsed.total_seconds() * 1000)
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


def _validate_scrape_output(**context) -> None:
    runs_dir = Path(Variable.get("raw_data_dir", default_var="/opt/airflow/data/raw")).parent / "runs"
    run_files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not run_files:
        raise ValueError("No run result files found")

    records_by_source: dict[str, int] = {}
    for run_file in run_files:
        data = json.loads(run_file.read_text())
        source = data["source"]
        if source not in records_by_source:
            records_by_source[source] = data["records_written"]
            context["task_instance"].xcom_push(
                key=f"records_written_{source}",
                value=data["records_written"],
            )

    zero_sources = [s for s, n in records_by_source.items() if n == 0]
    if zero_sources:
        raise ValueError(f"Zero records written for: {', '.join(zero_sources)}")


default_args = {
    "owner": "anuarhage",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": alert_on_failure,
    "sla": timedelta(hours=2),
}

with DAG(
    dag_id="alt_cards_scrape",
    schedule_interval="0 */6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["alt", "scraping", "phase1"],
    default_args=default_args,
) as dag:

    check_availability = PythonOperator(
        task_id="check_source_availability",
        python_callable=_check_source_availability,
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

    validate_output = PythonOperator(
        task_id="validate_scrape_output",
        python_callable=_validate_scrape_output,
    )

    trigger_process = TriggerDagRunOperator(
        task_id="trigger_process_dag",
        trigger_dag_id="alt_cards_process",
        wait_for_completion=False,
    )

    check_availability >> [scrape_ebay, scrape_pwcc] >> validate_output >> trigger_process
