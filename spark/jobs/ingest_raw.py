import logging
import os

from pyspark.sql import Window
from pyspark.sql.functions import (
    col,
    current_date,
    current_timestamp,
    desc,
    input_file_name,
    row_number,
)

from spark.schemas.raw_card_sale import RAW_CARD_SALE_SCHEMA
from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)

RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "data/raw")


def run(source: str | None = None) -> None:
    spark = get_spark_session("ingest_raw")

    pattern = f"{RAW_DATA_DIR}/{source or '*'}/year=*/month=*/day=*/*.ndjson"
    logger.info("Reading ndjson files: %s", pattern)

    df = (
        spark.read.schema(RAW_CARD_SALE_SCHEMA)
        .option("multiline", "false")
        .json(pattern)
    )

    total = df.count()
    logger.info("Total records read: %d", total)

    _log_validation(df)

    df = _deduplicate(df)

    df = (
        df.withColumn("ingested_at", current_timestamp())
        .withColumn("processing_date", current_date())
        .withColumn("source_file", input_file_name())
    )

    output_dir = os.getenv("PROCESSED_DATA_DIR", "data/processed/ingested")
    (
        df.write.mode("overwrite")
        .option("partitionOverwriteMode", "dynamic")
        .partitionBy("source", "processing_date")
        .parquet(output_dir)
    )
    logger.info("Wrote ingested data to %s", output_dir)


def _log_validation(df) -> None:
    null_price = df.filter(col("sale_price_usd").isNull()).count()
    invalid_price = df.filter(col("sale_price_usd") <= 0).count()
    null_date = df.filter(col("sale_date").isNull()).count()
    null_id = df.filter(col("listing_id").isNull()).count()

    from pyspark.sql.functions import count as spark_count

    dup_hashes = (
        df.groupBy("record_hash")
        .agg(spark_count("*").alias("cnt"))
        .filter(col("cnt") > 1)
        .count()
    )

    logger.warning("null_price_count=%d", null_price)
    logger.warning("invalid_price_count=%d", invalid_price)
    logger.warning("null_date_count=%d", null_date)
    logger.warning("null_id_count=%d", null_id)
    logger.warning("duplicate_hash_count=%d", dup_hashes)


def _deduplicate(df):
    window = Window.partitionBy("record_hash").orderBy(desc("scraped_at"))
    return (
        df.withColumn("rn", row_number().over(window))
        .filter(col("rn") == 1)
        .drop("rn")
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    run(source=args.source)
