"""
Cache manager for SpecWatch.
Provides high-level cache operations and invalidation strategies.
"""

from typing import List, Optional
from specwatch.cache.redis_client import get_redis_client
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Manages cache operations and invalidation
class CacheManager:
    
    # Initialize cache manager
    def __init__(self):

        self.redis = get_redis_client()
    
    # ========================================
    # Discovery Cache Operations
    # ========================================
    
    # Get cached Tavily search result
    def get_discovery_result(self, query: str) -> Optional[str]:

        key = f"tavily:search:{query}"
        return self.redis.get(key)
    
    # Cache Tavily search result (7 days)
    def set_discovery_result(self, query: str, result: str, ttl: int = 604800):

        key = f"tavily:search:{query}"
        self.redis.set(key, result, ttl=ttl)
    
    # Get cached discovery result for vendor
    def get_vendor_discovery(self, vendor: str) -> Optional[str]:

        key = f"discovery:{vendor}"
        return self.redis.get(key)
    
    # Cache vendor discovery result (7 days)
    def set_vendor_discovery(self, vendor: str, discovery: str, ttl: int = 604800):

        key = f"discovery:{vendor}"
        self.redis.set(key, discovery, ttl=ttl)
    
    # ========================================
    # Spec Hash Cache Operations
    # ========================================
    
    # Get cached spec hash for vendor
    def get_spec_hash(self, vendor: str) -> Optional[str]:

        key = f"spec:hash:{vendor}"
        return self.redis.get(key)
    
    # Cache spec hash for vendor (NO TTL: permanent)
    def set_spec_hash(self, vendor: str, spec_hash: str):

        key = f"spec:hash:{vendor}"
        self.redis.set(key, spec_hash)
    
    # ========================================
    # Classification Cache Operations
    # ========================================
    
    # Get cached classification result
    def get_classification(self, diff_hash: str) -> Optional[str]:

        key = f"classification:{diff_hash}"
        return self.redis.get(key)
    
    # Cache classification result (30 days)
    def set_classification(self, diff_hash: str, classification: str, ttl: int = 2592000):

        key = f"classification:{diff_hash}"
        self.redis.set(key, classification, ttl=ttl)
    
    # ========================================
    # Cache Invalidation
    # ========================================
    
    # Invalidate all caches for a specific vendor
    def invalidate_vendor(self, vendor: str):

        patterns = [
            f"discovery:{vendor}",
            f"spec:hash:{vendor}",
            f"tavily:search:*{vendor}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            keys = self.redis.keys(pattern)
            for key in keys:
                if self.redis.delete(key):
                    total_deleted += 1
        
        logger.info(f"Invalidated {total_deleted} cache entries for vendor '{vendor}'")
    
    # Invalidate all discovery caches
    def invalidate_discovery(self):

        patterns = ["tavily:search:*", "discovery:*"]
        
        total_deleted = 0
        for pattern in patterns:
            keys = self.redis.keys(pattern)
            for key in keys:
                if self.redis.delete(key):
                    total_deleted += 1
        
        logger.info(f"Invalidated {total_deleted} discovery cache entries")
    
    # Invalidate all classification caches
    def invalidate_classifications(self):

        keys = self.redis.keys("classification:*")
        total_deleted = sum(1 for key in keys if self.redis.delete(key))
        
        logger.info(f"Invalidated {total_deleted} classification cache entries")
    
    # Clear entire cache
    def clear_all(self):

        if self.redis.flushdb():
            logger.warning("Entire cache cleared")
    
    # ========================================
    # Cache Statistics
    # ========================================
    
    # Get cache statistics
    def get_stats(self) -> dict:

        if not self.redis.is_available():
            return {
                "enabled": False,
                "connected": False
            }
        
        info = self.redis.info()
        
        # Count keys by type
        discovery_keys = len(self.redis.keys("tavily:search:*"))
        vendor_discovery_keys = len(self.redis.keys("discovery:*"))
        spec_hash_keys = len(self.redis.keys("spec:hash:*"))
        classification_keys = len(self.redis.keys("classification:*"))
        
        return {
            "enabled": True,
            "connected": True,
            "total_keys": self.redis.dbsize(),
            "keys_by_type": {
                "tavily_searches": discovery_keys,
                "vendor_discoveries": vendor_discovery_keys,
                "spec_hashes": spec_hash_keys,
                "classifications": classification_keys
            },
            "memory": {
                "used": info.get('used_memory_human', 'N/A'),
                "peak": info.get('used_memory_peak_human', 'N/A')
            },
            "stats": {
                "uptime_seconds": info.get('uptime_in_seconds', 0),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0)
            }
        }
    
    # Get cache info for specific vendor
    def get_vendor_cache_info(self, vendor: str) -> dict:

        return {
            "vendor": vendor,
            "discovery_cached": self.redis.exists(f"discovery:{vendor}"),
            "discovery_ttl": self.redis.ttl(f"discovery:{vendor}"),
            "spec_hash_cached": self.redis.exists(f"spec:hash:{vendor}"),
            "tavily_searches_cached": len(self.redis.keys(f"tavily:search:*{vendor}*"))
        }
