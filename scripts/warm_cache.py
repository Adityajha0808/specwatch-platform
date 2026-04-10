#!/usr/bin/env python3
"""
Warm cache with common queries.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from specwatch.config.config_loader import load_vendors, load_queries
from specwatch.discovery.tavily_client import TavilyClient


# Pre-populate discovery cache
def warm_discovery_cache():

    vendors = load_vendors()
    query_templates = load_queries()
    
    client = TavilyClient()
    
    print("Warming discovery cache...")
    
    for vendor in vendors:
        display_name = vendor['display_name']
        
        for source_type, template in query_templates.items():
            query = template.replace("{vendor}", display_name)
            
            print(f"  Warming: {query}")
            client.search(query)
    
    print("✓ Cache warming complete!")


if __name__ == '__main__':
    warm_discovery_cache()
