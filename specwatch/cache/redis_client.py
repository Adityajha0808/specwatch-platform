"""
Redis client for SpecWatch caching.
Provides connection management with graceful degradation.
If Redis is unavailable, caching is disabled but pipelines continue.

-- Check all keys stored in cache: ``` redis-cli KEYS "*" ```
-- Check json details of a specific key: ``` redis-cli GET "tavily:search:Stripe API documentation:5" ```
-- Clear entire cache: ``` curl -X POST http://localhost:5050/api/cache/clear ```
"""


import redis
import os
from specwatch.utils.logger import get_logger
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime

load_dotenv()

logger = get_logger(__name__)


# Redis connection manager with graceful degradation
class RedisClient:
    
    # Initialize Redis connection
    def __init__(self):

        self.client: Optional[redis.Redis] = None
        self.enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
        self._connect()
    
    # Establish Redis connection
    def _connect(self):

        if not self.enabled:
            logger.info("Redis caching disabled (REDIS_ENABLED=false)")
            return
        
        try:
            self.client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis connected: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
        
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled, continuing without cache.")
            self.client = None
        
        except Exception as e:
            logger.error(f"Redis initialization error: {e}. Caching disabled.")
            self.client = None
    
    # Check if Redis is available
    def is_available(self) -> bool:

        return self.client is not None
    
    # Get value from cache
    def get(self, key: str) -> Optional[str]:

        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        
        except Exception as e:
            logger.warning(f"Cache GET error for key '{key}': {e}")
            return None
    
    # Set value in cache with optional TTL
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:

        if not self.is_available():
            return False
        
        try:
            if ttl:
                self.client.setex(key, ttl, value)
                logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            else:
                self.client.set(key, value)
                logger.debug(f"Cache SET: {key} (no expiration)")
            return True
        
        except Exception as e:
            logger.warning(f"Cache SET error for key '{key}': {e}")
            return False
    
    # Delete key from cache
    def delete(self, key: str) -> bool:

        if not self.is_available():
            return False
        
        try:
            result = self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
        
        except Exception as e:
            logger.warning(f"Cache DELETE error for key '{key}': {e}")
            return False
    
    # Check if key exists in cache
    def exists(self, key: str) -> bool:

        if not self.is_available():
            return False
        
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache EXISTS error for key '{key}': {e}")
            return False
    
    # Get all keys matching pattern
    def keys(self, pattern: str) -> list:

        if not self.is_available():
            return []
        
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.warning(f"Cache KEYS error for pattern '{pattern}': {e}")
            return []
    
    # Get remaining TTL for key
    def ttl(self, key: str) -> int:

        if not self.is_available():
            return -2
        
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache TTL error for key '{key}': {e}")
            return -2
    
    # Get Redis server info
    def info(self) -> dict:

        if not self.is_available():
            return {}
        
        try:
            return self.client.info()
        except Exception as e:
            logger.warning(f"Cache INFO error: {e}")
            return {}
    
    # Get number of keys in current database
    def dbsize(self) -> int:

        if not self.is_available():
            return 0
        
        try:
            return self.client.dbsize()
        except Exception as e:
            logger.warning(f"Cache DBSIZE error: {e}")
            return 0
    
    # Clear all keys in current database
    def flushdb(self) -> bool:

        if not self.is_available():
            return False
        
        try:
            self.client.flushdb()
            logger.warning("Cache cleared (FLUSHDB)")
            return True
        except Exception as e:
            logger.error(f"Cache FLUSHDB error: {e}")
            return False


# Global singleton instance
_redis_client: Optional[RedisClient] = None


# Get global Redis client instance
def get_redis_client() -> RedisClient:

    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
