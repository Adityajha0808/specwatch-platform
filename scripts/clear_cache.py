#!/usr/bin/env python3
"""
Clear Redis cache.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from specwatch.cache.cache_manager import CacheManager


# Clear entire cache
def clear_cache():

    cache_manager = CacheManager()
    
    confirm = input("Are you sure you want to clear the entire cache? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return
    
    cache_manager.clear_all()
    print("✓ Cache cleared successfully!")


if __name__ == '__main__':
    clear_cache()
