"""
Run GE data quality checks against the latest enriched parquet.

Usage (local):
    python great_expectations/run_checkpoint.py

Usage (Airflow BashOperator):
    cd /opt/airflow && python great_expectations/run_checkpoint.py

Exits with code 1 if any expectation fails.
Data Docs HTML: great_expectations/uncommitted/data_docs/local_site/index.html
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
GE_DIR = PROJECT_ROOT / "great_expectations"
ENRICHED_DIR = PROJECT_ROOT / "data" / "processed" / "enriched"


def main() -> None:
    try:
        import great_expectations as gx
        import pandas as pd
        from great_expectations.data_context import DataContext
    except ImportError as exc:
        print(f"[GE] Missing dependency: {exc}. Install: pip install great-expectations==0.18.12 pandas pyarrow")
        sys.exit(1)

    if not ENRICHED_DIR.exists():
        print(f"[GE] Enriched data not found: {ENRICHED_DIR}")
        print("[GE] Run the Spark pipeline first: make spark-all")
        sys.exit(1)

    print(f"[GE] Loading enriched parquet from {ENRICHED_DIR}")
    df = pd.read_parquet(ENRICHED_DIR)
    print(f"[GE] Loaded {len(df):,} rows, {len(df.columns)} columns")

    context = DataContext(context_root_dir=str(GE_DIR))

    # Register the pandas datasource with a dataframe asset (idempotent).
    datasource = context.sources.add_or_update_pandas(name="card_sales_pandas")
    asset = datasource.add_dataframe_asset(name="fct_card_sales")
    batch_request = asset.build_batch_request(dataframe=df)

    # Build an in-process SimpleCheckpoint (no YAML checkpoint required at runtime).
    checkpoint = gx.checkpoint.SimpleCheckpoint(
        name="card_sales_checkpoint",
        data_context=context,
        validations=[
            {
                "batch_request": batch_request,
                "expectation_suite_name": "fct_card_sales_suite",
            }
        ],
        action_list=[
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction", "site_names": []},
            },
        ],
    )

    results = checkpoint.run()
    success = results["success"]

    evaluated = failed = 0
    for vr in results.list_validation_results():
        s = vr.statistics
        evaluated += s.get("evaluated_expectations", 0)
        failed += s.get("unsuccessful_expectations", 0)

    print(f"[GE] Result: {'PASS' if success else 'FAIL'} — {evaluated} evaluated, {failed} failed")
    docs_path = GE_DIR / "uncommitted" / "data_docs" / "local_site" / "index.html"
    print(f"[GE] Data Docs: {docs_path}")

    if not success:
        for vr in results.list_validation_results():
            for r in vr.results:
                if not r.success:
                    col = r.expectation_config.kwargs.get("column", "table")
                    print(f"[GE] FAILED: {r.expectation_config.expectation_type} on '{col}' — {r.result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
