# Run discovery layer pipeline
# Added logging, Query result ranking, url validation and Vendor Onboarding Script

from specwatch.discovery.tavily_client import tavily_search
from specwatch.discovery.source_resolver import resolve_best_source
from specwatch.config.config_loader import (
    load_vendors,
    load_vendor_registry,
    load_queries
)

from specwatch.config.config_validator import validate_configs
from specwatch.store.raw_discovery_store import store_raw
from specwatch.store.discovery_store import store_latest_discovery
from specwatch.utils.logger import get_logger
from datetime import datetime, UTC


logger = get_logger(__name__)


def run_discovery():

    vendors = load_vendors()
    registry = load_vendor_registry()
    query_templates = load_queries()

    validate_configs(vendors, registry, query_templates)

    logger.info("Starting discovery pipeline")

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
    run_discovery()