import os

from pyspark.sql import SparkSession


def get_spark_session(app_name: str) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.parquet.enableVectorizedReader", "true")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
    )

    gcs_bucket = os.getenv("GCS_TEMP_BUCKET")
    if gcs_bucket:
        builder = builder.config(
            "spark.sql.extensions", "com.google.cloud.spark.bigquery"
        )

    spark = builder.getOrCreate()

    if gcs_bucket:
        spark.conf.set("temporaryGcsBucket", gcs_bucket)

    return spark
