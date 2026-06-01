from pyspark.sql.types import (
    DateType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

RAW_CARD_SALE_SCHEMA = StructType(
    [
        StructField("listing_id", StringType(), nullable=False),
        StructField("source", StringType(), nullable=False),
        StructField("scraped_at", TimestampType(), nullable=False),
        StructField("sale_price_usd", DecimalType(12, 2), nullable=False),
        StructField("sale_date", DateType(), nullable=False),
        StructField("listing_title", StringType(), nullable=False),
        StructField("fighter_name", StringType(), nullable=True),
        StructField("card_year", IntegerType(), nullable=True),
        StructField("card_set", StringType(), nullable=True),
        StructField("card_number", StringType(), nullable=True),
        StructField("grade", StringType(), nullable=True),
        StructField("grader", StringType(), nullable=True),
        StructField("grade_numeric", DoubleType(), nullable=True),
        StructField("listing_url", StringType(), nullable=False),
        StructField("image_url", StringType(), nullable=True),
        StructField("sale_type", StringType(), nullable=False),
        StructField("record_hash", StringType(), nullable=False),
    ]
)
