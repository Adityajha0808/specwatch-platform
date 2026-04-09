import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient as TavilyAPIClient

from specwatch.cache.cache_manager import CacheManager
from specwatch.cache.cache_metrics import get_cache_metrics
from specwatch.utils.logger import get_logger


load_dotenv()

logger = get_logger(__name__)


# Tavily API client with Redis caching
class TavilyClient:

    CACHE_TTL = 604800  # 7 days

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

        self.client = TavilyAPIClient(api_key=api_key)
        self.cache = CacheManager()
        self.metrics = get_cache_metrics()

    # Search Tavily with Redis cache
    def search(self, query: str, max_results: int = 5):

        cache_key = f"{query}:{max_results}"

        # Try cache first
        try:
            cached = self.cache.get_discovery_result(cache_key)

            if cached:
                self.metrics.record_discovery_hit()
                logger.info(f"Cache HIT for query: {query}")
                return json.loads(cached)

            self.metrics.record_discovery_miss()
            logger.info(f"Cache MISS for query: {query}")

        except Exception as e:
            logger.warning(f"Cache read failed for query '{query}': {e}")

        # Fetch from Tavily
        results = self._fetch_from_tavily(query, max_results)

        # Cache result
        try:
            self.cache.set_discovery_result(
                cache_key,
                json.dumps(results),
                ttl=self.CACHE_TTL
            )
        except Exception as e:
            logger.warning(f"Cache write failed for query '{query}': {e}")

        return results

    # Fetch results directly from Tavily API
    def _fetch_from_tavily(self, query: str, max_results: int = 5):

        logger.info(f"Running Tavily search: {query}")

        try:
            response = self.client.search(
                query=query,
                search_depth="basic",
                max_results=max_results
            )

            results = response.get("results", [])

            if not results:
                logger.warning("Tavily returned no results")

            return results

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


# Backwards-compatible helper function: Execute Tavily search query with Redis caching
def tavily_search(query: str, max_results: int = 5):

    client = TavilyClient()
    return client.search(query, max_results)
