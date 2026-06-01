import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    lit,
    percentile_approx,
    when,
)

from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "data/processed")

SALE_TYPE_MAP = {
    "auction": "AUCTION",
    "buy_it_now": "BUY_IT_NOW",
    "best_offer": "BUY_IT_NOW",
}

IQR_MULTIPLIER = 3.0


def run() -> None:
    spark = get_spark_session("normalise_prices")

    input_path = f"{PROCESSED_DATA_DIR}/ingested"
    df = spark.read.parquet(input_path)
    logger.info("Read %d records from %s", df.count(), input_path)

    df = _add_buyer_premium(df)
    df = _flag_outliers(df, spark)
    df = _normalise_sale_type(df)

    output_path = f"{PROCESSED_DATA_DIR}/normalised"
    (
        df.write.mode("overwrite")
        .option("partitionOverwriteMode", "dynamic")
        .partitionBy("source", "processing_date")
        .parquet(output_path)
    )
    logger.info("Wrote normalised data to %s", output_path)


def _add_buyer_premium(df):
    return df.withColumn(
        "includes_buyer_premium",
        when(col("source") == "pwcc", lit(True)).otherwise(lit(False)),
    )


def _flag_outliers(df, spark: SparkSession):
    stats = (
        df.groupBy("source", "grade")
        .agg(
            percentile_approx("sale_price_usd", 0.25).alias("q1"),
            percentile_approx("sale_price_usd", 0.75).alias("q3"),
        )
        .withColumn("iqr", col("q3") - col("q1"))
        .withColumn("lower_bound", col("q1") - IQR_MULTIPLIER * col("iqr"))
        .withColumn("upper_bound", col("q3") + IQR_MULTIPLIER * col("iqr"))
    )

    df = df.join(stats, on=["source", "grade"], how="left")
    df = df.withColumn(
        "is_outlier",
        when(col("lower_bound").isNull(), lit(False))
        .when(col("sale_price_usd") < col("lower_bound"), lit(True))
        .when(col("sale_price_usd") > col("upper_bound"), lit(True))
        .otherwise(lit(False)),
    )
    return df.drop("q1", "q3", "iqr", "lower_bound", "upper_bound")


def _normalise_sale_type(df):
    mapping_expr = (
        when(col("sale_type") == "auction", lit("AUCTION"))
        .when(col("sale_type") == "buy_it_now", lit("BUY_IT_NOW"))
        .when(col("sale_type") == "best_offer", lit("BUY_IT_NOW"))
        .otherwise(lit("UNKNOWN"))
    )
    return df.withColumn("sale_type", mapping_expr)


if __name__ == "__main__":
    run()
