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
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if gcs_bucket:
        builder = builder.config(
            "spark.jars.packages",
            "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.36.1",
        )
        if credentials_path:
            builder = builder.config(
                "spark.hadoop.google.cloud.auth.service.account.json.keyfile", credentials_path
            )

    spark = builder.getOrCreate()

    return spark
