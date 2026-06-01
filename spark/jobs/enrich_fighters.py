import logging
import os

from pyspark.sql.functions import col, lit, lower, trim, udf, when
from pyspark.sql.types import StringType

from spark.utils.fighter_lookup import FIGHTER_ALIASES
from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "data/processed")

MMA_KEYWORDS = {"ufc", "bellator", "one fc", "one championship", "mma", "pfl", "cage warriors"}
BOXING_KEYWORDS = {"prizm", "topps chrome", "boxing", "wbc", "wba", "ibf", "wbo"}
BOXING_FIGHTERS = {name.lower() for name in FIGHTER_ALIASES.values() if "boxing" in name.lower()}


def run() -> None:
    spark = get_spark_session("enrich_fighters")

    input_path = f"{PROCESSED_DATA_DIR}/normalised"
    df = spark.read.parquet(input_path)

    aliases_broadcast = spark.sparkContext.broadcast(FIGHTER_ALIASES)

    @udf(returnType=StringType())
    def resolve_fighter(raw_name, title):
        aliases = aliases_broadcast.value
        if raw_name:
            key = raw_name.strip().lower()
            if key in aliases:
                return aliases[key]
        if title:
            title_lower = title.lower()
            for alias, canonical in aliases.items():
                if alias in title_lower:
                    return canonical
        return None

    @udf(returnType=StringType())
    def classify_sport(card_set, fighter_canonical):
        parts = [card_set or "", fighter_canonical or ""]
        combined = " ".join(parts).lower()
        for kw in MMA_KEYWORDS:
            if kw in combined:
                return "MMA"
        for kw in BOXING_KEYWORDS:
            if kw in combined:
                return "BOXING"
        return "UNKNOWN"

    df = df.withColumn(
        "fighter_name_canonical",
        resolve_fighter(col("fighter_name"), col("listing_title")),
    )
    df = df.withColumn(
        "sport",
        classify_sport(col("card_set"), col("fighter_name_canonical")),
    )

    output_path = f"{PROCESSED_DATA_DIR}/enriched"
    (
        df.write.mode("overwrite")
        .option("partitionOverwriteMode", "dynamic")
        .partitionBy("source", "processing_date")
        .parquet(output_path)
    )
    logger.info("Wrote enriched data to %s", output_path)


if __name__ == "__main__":
    run()
