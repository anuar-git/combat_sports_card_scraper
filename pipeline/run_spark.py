import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = ["ingest", "normalise", "enrich", "benchmarks"]


def run_step(step: str, source: str | None) -> None:
    if step == "ingest":
        from spark.jobs.ingest_raw import run
        run(source=source)
    elif step == "normalise":
        from spark.jobs.normalise_prices import run
        run()
    elif step == "enrich":
        from spark.jobs.enrich_fighters import run
        run()
    elif step == "benchmarks":
        from spark.jobs.compute_benchmarks import run
        run()
    else:
        raise ValueError(f"Unknown step: {step}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PySpark processing pipeline")
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=STEPS + ["all"],
        default=["all"],
        help="Pipeline steps to run (default: all)",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Limit ingest to a specific source (ebay, pwcc, goldin)",
    )
    args = parser.parse_args()

    steps = STEPS if "all" in args.steps else args.steps

    for step in steps:
        logger.info("Starting step: %s", step)
        run_step(step, source=args.source)
        logger.info("Completed step: %s", step)

    logger.info("Pipeline finished. Steps ran: %s", steps)


if __name__ == "__main__":
    main()
