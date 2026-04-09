#!/usr/bin/env python3
"""
Runs ingestion layer pipeline - Get raw OpenAPI spec from discovered sources.

Supports vendor-specific execution:
    python3 -m pipelines.ingestion_pipeline                  # All vendors
    python3 -m pipelines.ingestion_pipeline --vendor stripe  # Specific vendor
"""

import os
import sys
import json
import argparse
from typing import List

from specwatch.ingestion.openapi_resolver import OpenAPIResolver
from specwatch.ingestion.spec_fetcher import fetch_spec
from specwatch.store.spec_store import store_spec
from specwatch.utils.logger import get_logger


logger = get_logger(__name__)


DISCOVERY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../storage/discovery")
)


resolver = OpenAPIResolver()


# Use discovery files as input for ingestion
def load_discovery_files():

    if not os.path.exists(DISCOVERY_PATH):
        logger.error("Discovery folder not found")
        return []

    files = []
    for file in sorted(os.listdir(DISCOVERY_PATH)):
        if file.endswith(".json"):
            files.append(os.path.join(DISCOVERY_PATH, file))

    return files


# Run ingestion pipeline with caching
def run_ingestion(vendors_input: List[str] = None) -> bool:

    logger.info("Starting ingestion pipeline")

    discovery_files = load_discovery_files()

    if not discovery_files:
        logger.warning("No discovery files found")
        return False

    # Filter vendors if specified
    vendor_filter = set(v.lower() for v in vendors_input) if vendors_input else None

    vendors_processed = 0
    vendors_skipped = 0
    vendors_failed = 0

    for file_path in discovery_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed reading discovery file {file_path}: {e}")
            continue

        vendor = data.get("vendor")
        sources = data.get("sources", {})

        if not vendor:
            logger.warning(f"Vendor missing in discovery file: {file_path}")
            continue

        vendor = vendor.lower()

        # Vendor-specific filtering
        if vendor_filter and vendor not in vendor_filter:
            logger.debug(f"Skipping vendor {vendor} (not in filter)")
            continue

        openapi_source = sources.get("openapi")

        if not openapi_source:
            logger.warning(f"No OpenAPI source for {vendor}")
            vendors_failed += 1
            continue

        logger.info(f"Processing OpenAPI source for {vendor}")

        # Resolve spec URL
        spec_url = resolver.resolve(vendor, openapi_source)

        if not spec_url:
            logger.warning(f"Could not resolve OpenAPI spec for {vendor}")
            vendors_failed += 1
            continue

        logger.info(f"Resolved spec URL for {vendor}: {spec_url}")

        # Fetch spec (with content-based caching)
        spec_content = fetch_spec(spec_url, vendor=vendor)

        # Handle cache skip signal
        if spec_content is None:
            logger.info(f"✓ Spec unchanged for {vendor} (cached hash match), skipping storage")
            vendors_skipped += 1
            continue

        # Store new/changed spec
        stored_file = store_spec(vendor, spec_content)

        if stored_file:
            logger.info(f"✓ Stored new spec for {vendor}: {stored_file}")
            vendors_processed += 1
        else:
            logger.error(f"Failed to store spec for {vendor}")
            vendors_failed += 1

    # Summary
    logger.info("="*60)
    logger.info(f"Ingestion pipeline completed:")
    logger.info(f"  - Processed (new/changed): {vendors_processed}")
    logger.info(f"  - Skipped (unchanged): {vendors_skipped}")
    logger.info(f"  - Failed: {vendors_failed}")
    logger.info("="*60)

    return True


# For Running ingestion pipeline standalone: python3 -m pipelines.ingestion_pipeline
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ingestion pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to process (e.g., stripe)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    logger.info("Ingestion pipeline CLI started")
    
    success = run_ingestion(vendors_input=args.vendors)
    
    logger.info("Ingestion pipeline CLI complete")
    sys.exit(0 if success else 1)
