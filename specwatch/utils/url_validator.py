import requests

from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


REQUEST_TIMEOUT = 5


def validate_url(url: str) -> bool:

    try:

        response = requests.head(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        status = response.status_code

        if status < 400:
            return True

        logger.warning(f"Invalid URL (status {status}): {url}")

        return False

    except requests.RequestException as e:

        logger.warning(f"URL validation failed: {url} | {e}")

        return False
