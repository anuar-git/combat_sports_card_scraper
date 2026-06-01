.PHONY: spark-ingest spark-normalise spark-enrich spark-benchmarks spark-all \
        dbt-run dbt-test dbt-freshness dbt-all test full-run

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
