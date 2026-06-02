"""Load enriched Parquet data into BigQuery alt_cards_raw dataset.

Reads data/processed/enriched, splits by source, and writes one table per
source into alt_cards_raw:
  - alt_cards_raw.ebay_sales
  - alt_cards_raw.pwcc_sales
  - alt_cards_raw.myslabs_sales

Requires GCS_TEMP_BUCKET and GCP_PROJECT_ID to be set.

Usage:
    python -m spark.jobs.load_to_bigquery
"""

import logging
import os

from pyspark.sql.functions import col

from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "data/processed")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCS_TEMP_BUCKET = os.getenv("GCS_TEMP_BUCKET", "")
BQ_RAW_DATASET = os.getenv("BQ_RAW_DATASET", "alt_cards_raw")

SOURCES = ["ebay", "pwcc", "myslabs"]


def run() -> None:
    if not GCP_PROJECT_ID or not GCS_TEMP_BUCKET:
        raise EnvironmentError("GCP_PROJECT_ID and GCS_TEMP_BUCKET must be set")

    spark = get_spark_session("load_to_bigquery")

    input_path = f"{PROCESSED_DATA_DIR}/enriched"
    df = spark.read.parquet(input_path)
    total = df.count()
    logger.info("Read %d enriched records from %s", total, input_path)

    for source in SOURCES:
        source_df = df.filter(col("source") == source).drop("processing_date")
        count = source_df.count()
        if count == 0:
            logger.info("No records for source=%s, skipping", source)
            continue

        table = f"{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.{source}_sales"
        logger.info("Writing %d records to %s", count, table)

        (
            source_df.write.format("bigquery")
            .option("table", table)
            .option("writeMethod", "direct")
            .option("partitionField", "sale_date")
            .option("partitionType", "DAY")
            .option("writeDisposition", "WRITE_TRUNCATE")
            .mode("overwrite")
            .save()
        )
        logger.info("Wrote %s successfully", table)


if __name__ == "__main__":
    run()
