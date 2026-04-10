#!/usr/bin/env python3
"""
Add vendor script with full configuration support.

Usage:
    python scripts/add_vendor.py <vendor_name> <display_name> [options]
    
Options:
    --openapi-url URL       OpenAPI specification URL
    --trusted-domains DOMAIN1,DOMAIN2,...  Trusted domains (comma-separated)
    
Example:
    python scripts/add_vendor.py stripe "Stripe" \
        --openapi-url "https://github.com/stripe/openapi" \
        --trusted-domains "stripe.com,github.com" \
"""

import sys
import json
import argparse
from pathlib import Path


# Add vendor to all configuration files
def add_vendor(
    vendor_name: str,
    display_name: str,
    openapi_url: str = None,
    trusted_domains: list = None
):
    
    config_dir = Path("specwatch/config/json")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    vendors_path = config_dir / "vendors.json"
    registry_path = config_dir / "vendor_registry.json"
    specs_path = config_dir / "vendor_specs.json"
    queries_path = config_dir / "discovery_queries.json"
    
    # 1. Add to vendors.json
    data = {"vendors": []}  # Initialize with the vendor dictionary structure

    if vendors_path.exists():
        try:
            with open(vendors_path, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except json.JSONDecodeError:
            print(f"Warning: {vendors_path} was corrupted, resetting.")
    
    # Extract the list from the dictionary
    vendors_list = data.get("vendors", [])
    
    # Check if already exists
    if any(v['name'] == vendor_name for v in vendors_list):
        print(f"Error: Vendor '{vendor_name}' already exists", file=sys.stderr)
        sys.exit(1)
    
    # Append the new vendor object
    new_vendor = {
        "name": vendor_name,
        "display_name": display_name
    }
    vendors_list.append(new_vendor)
    
    # Update the dictionary and save
    data["vendors"] = vendors_list

    with open(vendors_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Added to vendors.json")
    
    # 2. Add to vendor_registry.json (if URLs provided)
    registry = {}
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    
    if trusted_domains:
        registry['vendors'][vendor_name] = {
            "trusted_domains": trusted_domains
        }
    
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"✓ Added to vendor_registry.json")
    
    # 3. Add to vendor_specs.json (if URLs provided)
    specs = {}
    if specs_path.exists():
        with open(specs_path, 'r') as f:
            specs = json.load(f)
    
    if openapi_url:
        specs[vendor_name] = openapi_url
        
        with open(specs_path, 'w') as f:
            json.dump(specs, f, indent=2)
        
        print(f"✓ Added to vendor_specs.json")


def main():
    parser = argparse.ArgumentParser(
        description="Add vendor to SpecWatch configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('vendor_name', help='Vendor ID (lowercase, no spaces)')
    parser.add_argument('display_name', help='Display name (e.g., "Stripe")')
    parser.add_argument('--openapi-url', help='OpenAPI specification URL')
    parser.add_argument('--trusted-domains', help='Trusted domains (comma-separated)')
    
    args = parser.parse_args()
    
    # Parse trusted domains
    trusted_domains = None
    if args.trusted_domains:
        trusted_domains = [d.strip() for d in args.trusted_domains.split(',')]
    
    add_vendor(
        vendor_name=args.vendor_name,
        display_name=args.display_name,
        openapi_url=args.openapi_url,
        trusted_domains=trusted_domains
    )


if __name__ == '__main__':
    main()
