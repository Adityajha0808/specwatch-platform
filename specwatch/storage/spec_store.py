import os
import hashlib
from datetime import datetime
from specwatch.utils.logger import get_logger


logger = get_logger(__name__)


BASE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../storage/raw/raw_specs")
)


def ensure_directory():

    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH, exist_ok=True)


def generate_filename(vendor, extension):

    timestamp = datetime.utcnow().replace(microsecond=0).isoformat().replace(":", "-")

    filename = f"{vendor}_openapi_{timestamp}.{extension}"

    return filename


def calculate_hash(content):

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_latest_spec_file(vendor):

    if not os.path.exists(BASE_PATH):
        return None

    files = [
        f for f in os.listdir(BASE_PATH)
        if f.startswith(f"{vendor}_openapi_")
    ]

    if not files:
        return None

    files.sort(reverse=True)

    return os.path.join(BASE_PATH, files[0])


def get_file_hash(filepath):

    try:

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return calculate_hash(content)

    except Exception:
        return None


# Store spec content at desired path
def store_spec(vendor, spec_content):

    ensure_directory()

    if not spec_content:
        logger.warning(f"No spec content to store for {vendor}")
        return None

    extension = "yaml"

    if spec_content.strip().startswith("{"):
        extension = "json"

    new_hash = calculate_hash(spec_content)

    latest_file = get_latest_spec_file(vendor)

    if latest_file:

        existing_hash = get_file_hash(latest_file)

        if existing_hash == new_hash:
            logger.info(f"Spec unchanged for {vendor}, skipping storage")
            return latest_file

    filename = generate_filename(vendor, extension)

    filepath = os.path.join(BASE_PATH, filename)

    try:

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(spec_content)

        logger.info(f"Stored OpenAPI spec: {filepath}")

        return filepath

    except Exception as e:

        logger.error(f"Failed to store spec for {vendor}: {e}")

        return None
