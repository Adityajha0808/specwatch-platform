from urllib.parse import urlparse

from specwatch.utils.logger import get_logger
from specwatch.utils.url_validator import validate_url

logger = get_logger(__name__)


# Enforce filtered trusted domains
def filter_trusted_sources(results, trusted_domains):

    filtered = []

    for r in results:

        url = r.get("url")

        if not url:
            continue

        domain = urlparse(url).netloc

        for trusted in trusted_domains:

            if trusted in domain:

                filtered.append(url)
                break

    return filtered


# Rank sources based on relevance
def rank_sources(urls):

    scored = []

    for url in urls:

        score = 0

        if "docs" in url:
            score += 3

        if "github" in url:
            score += 2

        if "api" in url:
            score += 1

        scored.append((url, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [u[0] for u in scored]


def resolve_best_source(results, trusted_domains):

    filtered = filter_trusted_sources(results, trusted_domains)

    if not filtered:
        return None

    ranked = rank_sources(filtered)

    for url in ranked:

        if validate_url(url):
            logger.info(f"Resolved source: {url}")
            return url

    logger.warning("No valid source found")

    return None
