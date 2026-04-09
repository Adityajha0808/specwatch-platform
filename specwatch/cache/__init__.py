"""
Cache layer for SpecWatch.
Provides Redis-based caching with graceful degradation.
"""

from specwatch.cache.redis_client import RedisClient, get_redis_client
from specwatch.cache.cache_manager import CacheManager
from specwatch.cache.cache_metrics import CacheMetrics

__all__ = [
    'RedisClient',
    'get_redis_client',
    'CacheManager',
    'CacheMetrics'
]
