import logging
import os

from pyspark.sql import Window
from pyspark.sql.functions import avg, col, count, current_date, when
from pyspark.sql.types import LongType

from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "data/processed")

SECONDS_PER_DAY = 86400


def run() -> None:
    spark = get_spark_session("compute_benchmarks")

    input_path = f"{PROCESSED_DATA_DIR}/enriched"
    df = spark.read.parquet(input_path)

    df = df.filter(
        col("fighter_name_canonical").isNotNull()
        & col("grade").isNotNull()
        & col("grader").isNotNull()
        & col("sale_price_usd").isNotNull()
        & col("is_outlier") == False  # noqa: E712
    )

    ts_col = col("sale_date").cast("timestamp").cast(LongType())
    df = df.withColumn("sale_ts", ts_col)

    partition_cols = ["fighter_name_canonical", "grade", "grader"]

    def range_window(days: int):
        return (
            Window.partitionBy(*partition_cols)
            .orderBy("sale_ts")
            .rangeBetween(-days * SECONDS_PER_DAY, 0)
        )

    w7 = range_window(7)
    w30 = range_window(30)
    w90 = range_window(90)

    df = (
        df.withColumn("vwap_7d", avg("sale_price_usd").over(w7))
        .withColumn("vwap_30d", avg("sale_price_usd").over(w30))
        .withColumn("vwap_90d", avg("sale_price_usd").over(w90))
        .withColumn("sale_count_7d", count("*").over(w7))
        .withColumn("sale_count_30d", count("*").over(w30))
        .withColumn(
            "price_pct_change_7d",
            when(
                col("vwap_7d").isNotNull() & (col("vwap_7d") != 0),
                (col("sale_price_usd") - col("vwap_7d")) / col("vwap_7d") * 100,
            ),
        )
        .withColumn(
            "price_pct_change_30d",
            when(
                col("vwap_30d").isNotNull() & (col("vwap_30d") != 0),
                (col("sale_price_usd") - col("vwap_30d")) / col("vwap_30d") * 100,
            ),
        )
        .withColumn("processing_date", current_date())
    )

    output_path = f"{PROCESSED_DATA_DIR}/benchmarks"
    (
        df.write.mode("overwrite")
        .option("partitionOverwriteMode", "dynamic")
        .partitionBy("processing_date")
        .parquet(output_path)
    )
    logger.info("Wrote benchmarks to %s", output_path)


if __name__ == "__main__":
    run()
