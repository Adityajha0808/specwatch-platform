import os
import json

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


BASE_PATH = os.path.dirname(__file__)
VENDOR_SPEC_FILE = os.path.join(BASE_PATH, "json/vendor_specs.json")

# Load specific vendor specs from configurations
def load_vendor_specs():

    if not os.path.exists(VENDOR_SPEC_FILE):
        logger.warning("vendor_specs.json not found")
        return {}

    try:

        with open(VENDOR_SPEC_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # normalize keys
            return {k.lower(): v for k, v in data.items()}

    except Exception as e:

        logger.error(f"Failed to load vendor specs: {e}")
        return {}
