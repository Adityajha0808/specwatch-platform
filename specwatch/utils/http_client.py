import requests
import time
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2


HEADERS = {
    "User-Agent": "SpecWatch/1.0"
}


def url_exists(url):

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.head(
                url,
                headers=HEADERS,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True
            )

            if response.status_code == 200:
                return True
            
            logger.warning(
                f"HEAD {response.status_code} for {url}"
            )

            if response.status_code == 404:
                return False

        except Exception as e:

            logger.warning(
                f"HEAD request failed ({attempt+1}/{MAX_RETRIES}) for {url}: {e}"
            )

        time.sleep(RETRY_DELAY)

    return False


# Centralized HTTP client with retries, timeout handling, consistent headers, and reuse across ingestion modules.
def http_get(url):

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=DEFAULT_TIMEOUT
            )

            if response.status_code == 200:
                return response

            logger.warning(
                f"HTTP {response.status_code} for {url}"
            )

        except Exception as e:

            logger.warning(
                f"Request failed ({attempt+1}/{MAX_RETRIES}) for {url}: {e}"
            )

        time.sleep(RETRY_DELAY)

    logger.error(f"Failed to fetch URL: {url}")

    return None
