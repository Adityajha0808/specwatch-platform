#!/usr/bin/env python
"""Add a new vendor to SpecWatch configuration."""

import json
import sys
import argparse
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
        f.write("\n")


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
    config["vendors"] = sorted(config["vendors"], key=lambda v: v["name"])

    save_json(VENDORS_PATH, config)


# Add vendor to vendor_registry.json
def add_to_vendor_registry(name: str, domains: list):
    config = load_json(REGISTRY_PATH)

    config["vendors"][name] = {
        "trusted_domains": domains
    }

    config["vendors"] = dict(sorted(config["vendors"].items()))
    save_json(REGISTRY_PATH, config)


# Add vendor to vendor_specs.json (optional)
def add_to_vendor_specs(name: str, spec_url: str):
    config = load_json(SPECS_PATH)

    config[name] = spec_url
    config = dict(sorted(config.items()))

    save_json(SPECS_PATH, config)


# Add vendor to specwatch
def add_vendor(name: str, display_name: str, domains: list, spec_url: str = None):
    name = name.strip().lower()

    if not name:
        raise ValueError("Vendor name cannot be empty")

    if vendor_exists(name):
        raise ValueError(f"Vendor '{name}' already exists")

    if "github.com" not in domains:
        domains.append("github.com")

    add_to_vendors_json(name, display_name)
    add_to_vendor_registry(name, domains)

    if spec_url:
        add_to_vendor_specs(name, spec_url)

    return True


# Interactive cli for vendor addition workflow
def interactive_cli():
    print("\n" + "=" * 60)
    print("Add New Vendor to SpecWatch")
    print("=" * 60 + "\n")

    name = input("Vendor slug: ").strip().lower()
    display_name = input("Display name: ").strip() or name.capitalize()

    domains_input = input("Domains (comma-separated): ").strip()
    domains = [d.strip() for d in domains_input.split(",") if d.strip()]

    spec_url = input("Spec URL (optional): ").strip()
    confirm = input("Add this vendor? (y/N): ").strip().lower()

    if confirm != "y":
        print("Cancelled")
        sys.exit(0)

    add_vendor(name, display_name, domains, spec_url)
    print(f"Vendor '{display_name}' added successfully")


# Main Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("display_name", nargs="?")
    parser.add_argument("--domains", default="")
    parser.add_argument("--spec-url", default="")

    args = parser.parse_args()

    if args.name and args.display_name:
        domains = [d.strip() for d in args.domains.split(",") if d.strip()]
        add_vendor(args.name, args.display_name, domains, args.spec_url)
    else:
        interactive_cli()
