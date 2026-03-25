import os
import json

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


# Extract discovery sources, fetch and store the spec
def run_ingestion():

    logger.info("Starting ingestion pipeline")

    discovery_files = load_discovery_files()

    if not discovery_files:
        logger.warning("No discovery files found")
        return

    vendors_processed = 0

    for file_path in discovery_files:

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed reading discovery file {file_path}: {e}")
            continue

        vendor = data.get("vendor")
        sources = data.get("sources", {})

        openapi_source = sources.get("openapi")

        if not openapi_source:
            logger.warning(f"No OpenAPI source for {vendor}")
            continue

        vendors_processed += 1

        logger.info(f"Processing OpenAPI source for {vendor}")
        logger.info(f"Resolving OpenAPI spec for {vendor}")

        spec_url = resolver.resolve(vendor, openapi_source)

        if not spec_url:
            logger.warning(f"Could not resolve OpenAPI spec for {vendor}")
            continue

        logger.info(f"Resolved spec URL for {vendor}: {spec_url}")

        spec_content = fetch_spec(spec_url)

        if not spec_content:
            logger.warning(f"Failed to fetch spec for {vendor}")
            continue

        store_spec(vendor, spec_content)

    logger.info(f"Ingestion pipeline completed. Vendors Processed = {vendors_processed}.")
