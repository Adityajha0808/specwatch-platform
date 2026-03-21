#!/usr/bin/env python
"""Add a new vendor to SpecWatch configuration."""

import json
import sys
from pathlib import Path


# Paths
CONFIG_DIR = Path("specwatch/config/json")
VENDORS_PATH = CONFIG_DIR / "vendors.json"
REGISTRY_PATH = CONFIG_DIR / "vendor_registry.json"
SPECS_PATH = CONFIG_DIR / "vendor_specs.json"


# Load JSON file
def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r") as f:
        return json.load(f)


# Save JSON file with formatting
def save_json(path: Path, data: dict):

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")  # Add trailing newline


# Check if vendor already exists in vendors.json
def vendor_exists(name: str) -> bool:

    vendors_config = load_json(VENDORS_PATH)
    return any(v["name"] == name for v in vendors_config["vendors"])


# Add vendor to vendors.json
def add_to_vendors_json(name: str, display_name: str):

    config = load_json(VENDORS_PATH)
    
    vendor = {
        "name": name,
        "display_name": display_name
    }
    
    config["vendors"].append(vendor)
    
    # Sort vendors alphabetically by name
    config["vendors"] = sorted(config["vendors"], key=lambda v: v["name"])
    
    save_json(VENDORS_PATH, config)
    print(f" Added to vendors.json")


# Add vendor to vendor_registry.json
def add_to_vendor_registry(name: str, domains: list):

    config = load_json(REGISTRY_PATH)
    
    config["vendors"][name] = {
        "trusted_domains": domains
    }
    
    # Sort vendors alphabetically
    config["vendors"] = dict(sorted(config["vendors"].items()))
    
    save_json(REGISTRY_PATH, config)
    print(f" Added to vendor_registry.json")


# Add vendor to vendor_specs.json (optional)
def add_to_vendor_specs(name: str, spec_url: str):

    config = load_json(SPECS_PATH)
    
    config[name] = spec_url
    
    # Sort vendors alphabetically
    config = dict(sorted(config.items()))
    
    save_json(SPECS_PATH, config)
    print(f" Added to vendor_specs.json")


# Interactive vendor addition workflow
def add_vendor():

    print("\n" + "="*60)
    print("Add New Vendor to SpecWatch")
    print("="*60 + "\n")
    
    # Step 1: Get vendor name (slug)
    name = input("Vendor slug (lowercase, e.g., 'stripe'): ").strip().lower()
    
    if not name:
        print(" Vendor name cannot be empty")
        sys.exit(1)
    
    if not name.isalnum() and "-" not in name and "_" not in name:
        print(" Vendor name must be alphanumeric (can include - or _)")
        sys.exit(1)
    
    # Check if vendor already exists
    if vendor_exists(name):
        print(f" Vendor '{name}' already exists in vendors.json")
        sys.exit(1)
    
    # Step 2: Get display name
    display_name = input(f"Display name (e.g., 'Stripe'): ").strip()
    
    if not display_name:
        display_name = name.capitalize()
        print(f"   Using default: {display_name}")
    
    # Step 3: Get trusted domains
    print("\nTrusted domains (comma-separated):")
    print("   Examples: stripe.com, docs.stripe.com, github.com")
    domains_input = input("Domains: ").strip()
    
    if not domains_input:
        print(" At least one trusted domain is required")
        sys.exit(1)
    
    domains = [d.strip() for d in domains_input.split(",") if d.strip()]
    
    # Always include github.com if not already present
    if "github.com" not in domains:
        domains.append("github.com")
        print("   Added github.com to trusted domains")
    
    # Step 4: Get OpenAPI spec URL (optional)
    print("\nOpenAPI spec URL (optional, press Enter to skip):")
    print("   Example: https://raw.githubusercontent.com/stripe/openapi/master/openapi.yaml")
    spec_url = input("Spec URL: ").strip()
    
    # Confirmation
    print("\n" + "-"*60)
    print("Vendor Configuration Summary:")
    print("-"*60)
    print(f"Name:          {name}")
    print(f"Display Name:  {display_name}")
    print(f"Domains:       {', '.join(domains)}")
    print(f"Spec URL:      {spec_url or 'Not provided'}")
    print("-"*60)
    
    confirm = input("\nAdd this vendor? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print(" Cancelled")
        sys.exit(0)
    
    # Add to config files
    print("\nAdding vendor to configuration files...")
    
    try:
        add_to_vendors_json(name, display_name)
        add_to_vendor_registry(name, domains)
        
        if spec_url:
            add_to_vendor_specs(name, spec_url)
        
        print("\n" + "="*60)
        print(f" Vendor '{display_name}' added successfully!")
        print("="*60)
        print("\nNext steps:")
        print(f"1. Run discovery: python -m pipelines.discovery_pipeline")
        print(f"2. Run ingestion: python -m pipelines.ingestion_pipeline")
        print(f"3. Run normalization: python -m pipelines.normalization_pipeline")
        print(f"\nOr run full pipeline: python main.py")
        
    except Exception as e:
        print(f"\n Error adding vendor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    add_vendor()
