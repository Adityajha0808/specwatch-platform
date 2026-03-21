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

            # If HEAD is unreliable then fallback to GET for certain cases
            if response.status_code in [403, 405, 500]:
                logger.warning(f"HEAD {response.status_code}, falling back to GET: {url}")

                get_resp = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=DEFAULT_TIMEOUT,
                    stream=True
                )

                if get_resp.status_code == 200:
                    return True

            if response.status_code == 404:
                return False

            logger.warning(f"HEAD {response.status_code} for {url}")

        except Exception as e:
            logger.warning(
                f"HEAD failed ({attempt+1}/{MAX_RETRIES}) for {url}: {e}"
            )

            # Fallback to GET even on exception
            try:
                get_resp = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=DEFAULT_TIMEOUT,
                    stream=True
                )

                if get_resp.status_code == 200:
                    return True

            except Exception as get_err:
                logger.warning(
                    f"GET fallback failed ({attempt+1}/{MAX_RETRIES}) for {url}: {get_err}"
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

            # Retry only for transient errors
            if response.status_code in [429, 500, 502, 503, 504]:
                logger.warning(
                    f"Retryable HTTP {response.status_code} for {url}"
                )
            else:
                logger.warning(
                    f"HTTP {response.status_code} for {url}"
                )
                return None

        except Exception as e:

            logger.warning(
                f"Request failed ({attempt+1}/{MAX_RETRIES}) for {url}: {e}"
            )

        time.sleep(RETRY_DELAY)

    logger.error(f"Failed to fetch URL after retries: {url}")
    return None
