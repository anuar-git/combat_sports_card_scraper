"""Streamlit pipeline monitoring dashboard.

Run with:
    streamlit run monitoring/dashboard/app.py --server.port 8501
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

METRICS_PATH = Path("./data/metrics/latest.json")
RUNS_DIR = Path("./data/runs")

STATUS_COLORS = {
    "healthy": "#2ecc71",
    "degraded": "#f39c12",
    "stale": "#e67e22",
    "error": "#e74c3c",
}

STATUS_EMOJI = {
    "healthy": "🟢",
    "degraded": "🟡",
    "stale": "🟠",
    "error": "🔴",
}


def _load_metrics() -> dict | None:
    if not METRICS_PATH.exists():
        return None
    try:
        return json.loads(METRICS_PATH.read_text())
    except Exception:
        return None


def _load_run_history() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    runs = []
    for run_file in sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:60]:
        try:
            runs.append(json.loads(run_file.read_text()))
        except Exception:
            continue
    return runs


def _relative_time(iso_str: str | None) -> str:
    if not iso_str:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except Exception:
        return iso_str


def render_dashboard() -> None:
    st.set_page_config(
        page_title="Alt Cards Pipeline Monitor",
        page_icon="📊",
        layout="wide",
    )

    st.title("Alt Cards Pipeline Monitor")

    metrics = _load_metrics()

    if metrics is None:
        st.error("No metrics file found at `data/metrics/latest.json`. Run the pipeline first.")
        return

    pipeline = metrics.get("pipeline", {})
    overall_status = pipeline.get("overall_status", "error")
    updated_at = metrics.get("updated_at")
    sources = metrics.get("sources", {})
    dbt = metrics.get("dbt", {})

    color = STATUS_COLORS.get(overall_status, "#95a5a6")
    emoji = STATUS_EMOJI.get(overall_status, "⚪")

    st.markdown(
        f"""
        <div style="background:{color};padding:16px 24px;border-radius:8px;margin-bottom:16px;">
            <h2 style="color:white;margin:0;">{emoji} Pipeline Status: {overall_status.upper()}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Last Updated", _relative_time(updated_at))
    col2.metric("Total Records (fct_card_sales)", f"{pipeline.get('total_records_in_fct_card_sales', 0):,}")
    col3.metric("Fighters with Coverage", pipeline.get("fighters_with_coverage", 0))

    st.divider()

    st.subheader("Source Status")
    if sources:
        rows = []
        for source_name, s in sources.items():
            rows.append(
                {
                    "Source": source_name.upper(),
                    "Status": f"{STATUS_EMOJI.get(s['status'], '⚪')} {s['status']}",
                    "Last Scrape": _relative_time(s.get("last_successful_scrape")),
                    "Records Written": s.get("last_run_records_written", 0),
                    "Invalid Records": s.get("last_run_records_invalid", 0),
                    "Data Lag (h)": round(s.get("lag_hours", 0), 2),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No source data available yet.")

    st.divider()

    st.subheader("Records Ingested Over Time")
    history = _load_run_history()
    if history:
        df_history = pd.DataFrame(
            [
                {
                    "started_at": h.get("started_at"),
                    "source": h.get("source", "unknown"),
                    "records_written": h.get("records_written", 0),
                }
                for h in history
            ]
        )
        df_history["started_at"] = pd.to_datetime(df_history["started_at"], utc=True, errors="coerce")
        df_history = df_history.dropna(subset=["started_at"]).sort_values("started_at")

        if not df_history.empty:
            fig = px.line(
                df_history,
                x="started_at",
                y="records_written",
                color="source",
                markers=True,
                title="Records Written per Run",
                labels={"started_at": "Date", "records_written": "Records Written", "source": "Source"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough run history to plot.")
    else:
        st.info("No run history found in `data/runs/`.")

    st.divider()

    st.subheader("dbt Test Results")
    dbt_status_icon = STATUS_EMOJI.get(dbt.get("status", "error"), "⚪")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Status", f"{dbt_status_icon} {dbt.get('status', 'unknown')}")
    col_b.metric("Tests Passed", dbt.get("tests_passed", 0))
    col_c.metric("Tests Failed", dbt.get("tests_failed", 0))
    col_d.metric("Last Run", _relative_time(dbt.get("last_run_at")))

    st.divider()

    st.subheader("Recent Errors (last 10)")
    all_errors = []
    for h in history[:20]:
        for err in h.get("errors", []):
            all_errors.append(
                {
                    "Timestamp": h.get("completed_at", ""),
                    "Source": h.get("source", ""),
                    "Error": err,
                }
            )

    if all_errors:
        st.dataframe(pd.DataFrame(all_errors[:10]), use_container_width=True, hide_index=True)
    else:
        st.success("No errors in recent runs.")

    st.caption(f"Auto-refreshes every 60 seconds. Last loaded: {_relative_time(updated_at)}")


if __name__ == "__main__":
    placeholder = st.empty()
    while True:
        with placeholder.container():
            render_dashboard()
        time.sleep(60)
        st.rerun()
else:
    render_dashboard()
