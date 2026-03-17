import os
from tavily import TavilyClient
from dotenv import load_dotenv

from specwatch.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = TavilyClient(TAVILY_API_KEY)


# Execute Tavily search query
def tavily_search(query: str, max_results: int = 5):

    logger.info(f"Running Tavily search: {query}")

    try:

        response = client.search(
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
