.PHONY: spark-ingest spark-normalise spark-enrich spark-benchmarks spark-all \
        dbt-run dbt-test dbt-freshness dbt-all test full-run \
        airflow-up airflow-down api dashboard

spark-ingest:
	python -m spark.jobs.ingest_raw

spark-normalise:
	python -m spark.jobs.normalise_prices

spark-enrich:
	python -m spark.jobs.enrich_fighters

spark-benchmarks:
	python -m spark.jobs.compute_benchmarks

spark-all: spark-ingest spark-normalise spark-enrich spark-benchmarks

dbt-run:
	cd dbt && dbt run --profiles-dir .

dbt-test:
	cd dbt && dbt test --profiles-dir .

dbt-freshness:
	cd dbt && dbt source freshness --profiles-dir .

dbt-all: dbt-run dbt-test

test:
	pytest tests/ -v

full-run: spark-all dbt-all

# Phase 3: Monitoring & Orchestration
airflow-up:
	docker compose up -d

airflow-down:
	docker compose down

api:
	uvicorn monitoring.api.main:app --reload --port 8000

dashboard:
	streamlit run monitoring/dashboard/app.py --server.port 8501
