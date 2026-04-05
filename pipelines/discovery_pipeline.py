"""
Runs discovery layer pipeline - Find API documentation sources using Tavily.

Supports vendor-specific execution:
    python3 -m pipelines.discovery_pipeline                  # All vendors
    python3 -m pipelines.discovery_pipeline --vendor stripe  # Specific vendor
"""

import os
import sys
import argparse
from typing import List, Tuple

from specwatch.discovery.tavily_client import tavily_search
from specwatch.discovery.source_resolver import resolve_best_source
from specwatch.config.config_loader import (
    load_vendors,
    load_single_vendor_detail,
    load_vendor_registry,
    load_queries
)

from specwatch.config.config_validator import validate_configs
from specwatch.store.raw_discovery_store import store_raw
from specwatch.store.discovery_store import store_latest_discovery
from specwatch.utils.logger import get_logger
from datetime import datetime, UTC


logger = get_logger(__name__)


def run_discovery(vendors_input: List[str] = None) -> bool:

    vendors = load_vendors()
    registry = load_vendor_registry()
    query_templates = load_queries()

    validate_configs(vendors, registry, query_templates)

    logger.info("Starting discovery pipeline")

    # Pick if vendor is specified
    if vendors_input:
        vendors = load_single_vendor_detail(vendors_input)


    for vendor in vendors:

        name = vendor["name"]
        display_name = vendor["display_name"]

        trusted_domains = registry[name]["trusted_domains"]

        logger.info(f"Running discovery for {display_name}")

        output = {
            "vendor": name,
            "api": display_name,
            "discovered_at": datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S'),
            "sources": {}
        }

        for source_type, template in query_templates.items():

            query = template.replace("{vendor}", display_name)

            logger.info(f"Running Tavily query: {query}")

            try:

                results = tavily_search(query)

                best_url = resolve_best_source(
                    results,
                    trusted_domains
                )

                output["sources"][source_type] = best_url

                logger.info(
                    f"{display_name} {source_type} source resolved: {best_url}"
                )

            except Exception as e:

                logger.error(
                    f"Discovery failed for {display_name} {source_type}: {e}"
                )

                output["sources"][source_type] = None

        # Store versioned raw discovery result
        store_raw(name, output)

        # Store latest discovery
        store_latest_discovery(name, output)

    logger.info("Discovery pipeline completed")


# For Running discovery pipeline standalone: python3 -m pipelines.discovery_pipeline
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run discovery pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to discover (e.g., stripe). If not specified, discover for all vendors."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Enable debug logging if requested
    if args.debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    logger.info("Discovery pipeline cli started")
    
    success = run_discovery(vendors_input=args.vendors)
    
    logger.info("Discovery pipeline cli complete")
    sys.exit(0 if success else 1)
