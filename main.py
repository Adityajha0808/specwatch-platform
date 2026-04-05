"""SpecWatch Platform - Main Entry Point"""

import sys
import argparse
from specwatch.utils.logger import get_logger
from pipelines.discovery_pipeline import run_discovery
from pipelines.ingestion_pipeline import run_ingestion
from pipelines.normalization_pipeline import run_normalization
from pipelines.diff_pipeline import run_diff
from pipelines.classification_pipeline import run_classification
from pipelines.alerting_pipeline import run_alerting


logger = get_logger(__name__)


def run_full_pipeline(vendors=None):

    logger.info("Specwatch pipeline started")
    
    # Step 1: Discovery
    logger.info("Running discovery pipeline")
    run_discovery(vendors_input=vendors)
    
    # Step 2: Ingestion
    logger.info("Running ingestion pipeline")
    run_ingestion(vendors_input=vendors)
    
    # Step 3: Normalization
    logger.info("Running normalization pipeline")
    run_normalization(vendors=vendors)

    # Step 4: Diff Engine
    logger.info("Running diff pipeline")
    run_diff(vendors=vendors)

    # Step 5: Classification
    logger.info("Running classification pipeline")
    run_classification(vendors=vendors)

    # Step 6: Alerting
    logger.info("Running alerting pipeline")
    run_alerting(vendors=vendors)
    
    logger.info("Specwatch pipeline complete")
    return True


# Run full Pipeline: python3 main.py
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run full SpecWatch pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to run full pipeline for"
    )

    args = parser.parse_args()

    success = run_full_pipeline(vendors=args.vendors)
    sys.exit(0 if success else 1)
