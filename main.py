"""SpecWatch Platform - Main Entry Point"""

import sys
from specwatch.utils.logger import get_logger
from pipelines.discovery_pipeline import run_discovery
from pipelines.ingestion_pipeline import run_ingestion
from pipelines.normalization_pipeline import run_normalization
from pipelines.diff_pipeline import run_diff

logger = get_logger(__name__)


def run_full_pipeline():

    logger.info("Specwatch pipeline started")
    
    # Step 1: Discovery
    logger.info("Running discovery pipeline")
    run_discovery()
    
    # Step 2: Ingestion
    logger.info("Running ingestion pipeline")
    run_ingestion()
    
    # Step 3: Normalization
    logger.info("Running normalization pipeline")
    run_normalization()

    # Step 4: Diff Engine
    logger.info("Running diff pipeline")
    run_diff()
    
    logger.info("Specwatch pipeline complete")
    return True


if __name__ == "__main__":
    
    success = run_full_pipeline()
    sys.exit(0 if success else 1)
