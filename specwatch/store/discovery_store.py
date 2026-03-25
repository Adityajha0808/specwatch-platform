# Store discovery files in desired location

import json
from pathlib import Path

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)

DISCOVERY_PATH = Path("storage/discovery")


def ensure_storage():

    DISCOVERY_PATH.mkdir(parents=True, exist_ok=True)


def get_vendor_file(vendor_name: str):

    return DISCOVERY_PATH / f"{vendor_name}.json"


def store_latest_discovery(vendor_name: str, data: dict):

    ensure_storage()

    file_path = get_vendor_file(vendor_name)

    try:

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Updated latest discovery snapshot: {file_path}")

    except Exception as e:

        logger.error(f"Failed to store discovery snapshot: {e}")


def load_latest_discovery(vendor_name: str):

    file_path = get_vendor_file(vendor_name)

    if not file_path.exists():
        return None

    try:

        with open(file_path, "r") as f:
            return json.load(f)

    except Exception as e:

        logger.error(f"Failed to read discovery snapshot: {e}")

        return None
