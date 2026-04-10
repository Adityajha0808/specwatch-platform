"""
Cache metrics tracking for SpecWatch.
Tracks cache hits and misses for performance monitoring.
"""

from datetime import datetime
from typing import Dict
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Tracks cache hit/miss statistics
class CacheMetrics:
    
    # Initialize metrics
    def __init__(self):

        self.discovery_hits = 0
        self.discovery_misses = 0
        self.spec_hash_hits = 0
        self.spec_hash_misses = 0
        self.classification_hits = 0
        self.classification_misses = 0
        self.started_at = datetime.utcnow()
    
    # ========================================
    # Discovery Metrics
    # ========================================
    
    # Record discovery cache hit
    def record_discovery_hit(self):

        self.discovery_hits += 1
        logger.debug("Discovery cache hit recorded")
    
    # Record discovery cache miss
    def record_discovery_miss(self):

        self.discovery_misses += 1
        logger.debug("Discovery cache miss recorded")
    
    # Get discovery cache hit rate
    def discovery_hit_rate(self) -> float:

        total = self.discovery_hits + self.discovery_misses
        return self.discovery_hits / total if total > 0 else 0.0
    
    # ========================================
    # Spec Hash Metrics
    # ========================================
    
    # Record spec hash cache hit
    def record_spec_hash_hit(self):

        self.spec_hash_hits += 1
        logger.debug("Spec hash cache hit recorded")
    
    # Record spec hash cache miss
    def record_spec_hash_miss(self):

        self.spec_hash_misses += 1
        logger.debug("Spec hash cache miss recorded")
    
    # Get spec hash cache hit rate
    def spec_hash_hit_rate(self) -> float:

        total = self.spec_hash_hits + self.spec_hash_misses
        return self.spec_hash_hits / total if total > 0 else 0.0
    
    # ========================================
    # Classification Metrics
    # ========================================
    
    # Record classification cache hit
    def record_classification_hit(self):

        self.classification_hits += 1
        logger.debug("Classification cache hit recorded")
    
    # Record classification cache miss
    def record_classification_miss(self):

        self.classification_misses += 1
        logger.debug("Classification cache miss recorded")
    
    # Get classification cache hit rate
    def classification_hit_rate(self) -> float:

        total = self.classification_hits + self.classification_misses
        return self.classification_hits / total if total > 0 else 0.0
    
    # ========================================
    # Overall Metrics
    # ========================================
    
    # Get overall cache hit rate
    def overall_hit_rate(self) -> float:

        total_hits = self.discovery_hits + self.spec_hash_hits + self.classification_hits
        total_misses = self.discovery_misses + self.spec_hash_misses + self.classification_misses
        total = total_hits + total_misses
        return total_hits / total if total > 0 else 0.0
    
    # Get metrics summary
    def get_summary(self) -> Dict:

        return {
            "started_at": self.started_at.isoformat(),
            "discovery": {
                "hits": self.discovery_hits,
                "misses": self.discovery_misses,
                "hit_rate": round(self.discovery_hit_rate(), 3)
            },
            "spec_hash": {
                "hits": self.spec_hash_hits,
                "misses": self.spec_hash_misses,
                "hit_rate": round(self.spec_hash_hit_rate(), 3)
            },
            "classification": {
                "hits": self.classification_hits,
                "misses": self.classification_misses,
                "hit_rate": round(self.classification_hit_rate(), 3)
            },
            "overall": {
                "total_hits": self.discovery_hits + self.spec_hash_hits + self.classification_hits,
                "total_misses": self.discovery_misses + self.spec_hash_misses + self.classification_misses,
                "hit_rate": round(self.overall_hit_rate(), 3)
            }
        }
    
    # Reset all metrics
    def reset(self):

        self.discovery_hits = 0
        self.discovery_misses = 0
        self.spec_hash_hits = 0
        self.spec_hash_misses = 0
        self.classification_hits = 0
        self.classification_misses = 0
        self.started_at = datetime.utcnow()
        logger.info("Cache metrics reset")


# Global singleton instance
_metrics: 'CacheMetrics' = None


# Get global cache metrics instance
def get_cache_metrics() -> CacheMetrics:

    global _metrics
    if _metrics is None:
        _metrics = CacheMetrics()
    return _metrics
