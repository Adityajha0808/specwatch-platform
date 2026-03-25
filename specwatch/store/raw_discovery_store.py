# Store versioned discovery outputs in root/storage/raw/raw_discovery folder.


import json
from pathlib import Path
from datetime import datetime

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)

RAW_STORAGE_PATH = Path("storage/raw/raw_discovery")


def ensure_storage():

    RAW_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def generate_filename(vendor_name: str):

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    return f"{vendor_name}_{timestamp}.json"


def store_raw(vendor_name: str, data: dict):

    ensure_storage()

    filename = generate_filename(vendor_name)

    file_path = RAW_STORAGE_PATH / filename

    try:

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Stored raw discovery file: {file_path}")

    except Exception as e:

        logger.error(f"Failed to store raw discovery data: {e}")
