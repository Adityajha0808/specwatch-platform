#!/usr/bin/env python3
"""
Spec fetcher with content-based hash caching.
"""

import hashlib
import requests

from specwatch.cache.cache_manager import CacheManager
from specwatch.cache.cache_metrics import get_cache_metrics
from specwatch.utils.logger import get_logger


logger = get_logger(__name__)


class SpecFetcher:

    
    # Initialize spec fetcher
    def __init__(self):

        self.session = requests.Session()
        self.cache = CacheManager()
        self.metrics = get_cache_metrics()
    
    # Fetch spec with content-based caching
    def fetch(self, url: str, vendor: str = None) -> str:

        try:
            # Step 1: Always fetch content (this is necessary)
            logger.info(f"Fetching OpenAPI spec: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            # Sanity check
            if len(content) < 100:
                logger.warning(f"Spec too small ({len(content)} bytes), possible invalid response: {url}")
                return None
            
            # Step 2: Compute content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            logger.debug(f"Computed content hash for {vendor}: {content_hash}")
            
            # Step 3: Compare with cached hash (if vendor provided)
            if vendor:
                cached_hash = self.cache.get_spec_hash(vendor)
                
                if cached_hash:
                    if cached_hash == content_hash:
                        # Content unchanged!
                        self.metrics.record_spec_hash_hit()
                        logger.info(f"✓ Spec content UNCHANGED for {vendor} (hash: {content_hash})")
                        logger.info(f"  → Skipping storage, normalization, diff, classification")
                        return None  # Signal: don't store, content is identical
                    else:
                        # Content changed!
                        self.metrics.record_spec_hash_miss()
                        logger.info(f"✗ Spec content CHANGED for {vendor}")
                        logger.info(f"  Old hash: {cached_hash}")
                        logger.info(f"  New hash: {content_hash}")
                else:
                    # No cached hash (first run)
                    self.metrics.record_spec_hash_miss()
                    logger.info(f"✗ No cached hash for {vendor}, treating as new")
                
                # Step 4: Update cache with new hash
                self.cache.set_spec_hash(vendor, content_hash)
                logger.debug(f"Updated cached hash for {vendor}: {content_hash}")
            
            # Step 5: Return content (it's new or changed)
            logger.info(f"✓ Returning spec content for {vendor} ({len(content)} bytes)")
            return content
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching spec: {url}")
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch spec: {url}, error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error fetching spec: {url}, error: {e}")
            return None


# Singleton instance (prevents recreating session/cache repeatedly)
_fetcher = SpecFetcher()


# Fetch spec with content-based caching
def fetch_spec(spec_url: str, vendor: str = None) -> str:

    return _fetcher.fetch(spec_url, vendor)
