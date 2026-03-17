from specwatch.utils.http_client import http_get
from specwatch.utils.logger import get_logger


logger = get_logger(__name__)

# Download spec content, validate response and return content
def fetch_spec(spec_url):

    if not spec_url:
        return None

    logger.info(f"Fetching OpenAPI spec: {spec_url}")

    response = http_get(spec_url)

    if not response:
        logger.error(f"Failed to fetch spec: {spec_url}")
        return None

    content = response.text

    if len(content) < 100:
        logger.warning(f"Spec too small, possible invalid response: {spec_url}")
        return None

    return content
