#!/usr/bin/env python
"""Remove a vendor from SpecWatch configuration."""


import json
import sys
import shutil
from pathlib import Path


# Paths
CONFIG_DIR = Path("specwatch/config/json")
VENDORS_PATH = CONFIG_DIR / "vendors.json"
REGISTRY_PATH = CONFIG_DIR / "vendor_registry.json"
SPECS_PATH = CONFIG_DIR / "vendor_specs.json"


STORAGE_PATHS = [
    Path("storage/discovery"),
    Path("storage/raw/discovery"),
    Path("storage/raw/raw_specs"),
    Path("storage/normalized")
]


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


# Check if vendor exists in vendors.json
def vendor_exists(name: str) -> bool:

    vendors_config = load_json(VENDORS_PATH)
    return any(v["name"] == name for v in vendors_config["vendors"])


# Remove vendor from vendors.json
def remove_from_vendors_json(name: str) -> bool:

    config = load_json(VENDORS_PATH)
    original_count = len(config["vendors"])
    
    config["vendors"] = [v for v in config["vendors"] if v["name"] != name]
    
    if len(config["vendors"]) == original_count:
        return False
    
    save_json(VENDORS_PATH, config)
    print(f" Removed from vendors.json")
    return True


# Remove vendor from vendor_registry.json
def remove_from_vendor_registry(name: str):

    config = load_json(REGISTRY_PATH)
    
    if name in config["vendors"]:
        del config["vendors"][name]
        save_json(REGISTRY_PATH, config)
        print(f" Removed from vendor_registry.json")
    else:
        print(f"  Not found in vendor_registry.json (skipped)")


# Remove vendor from vendor_specs.json
def remove_from_vendor_specs(name: str):

    config = load_json(SPECS_PATH)
    
    if name in config:
        del config[name]
        save_json(SPECS_PATH, config)
        print(f" Removed from vendor_specs.json")
    else:
        print(f"  Not found in vendor_specs.json (skipped)")


# Find all storage locations for a vendor
def find_vendor_storage(name: str) -> dict:

    storage_locations = {}
    
    for base_path in STORAGE_PATHS:
        if not base_path.exists():
            continue
        
        # Check for vendor-specific files/directories
        vendor_items = []
        
        if base_path.name == "raw_discovery" and base_path.parent.name == "raw":
            # storage/raw/raw_discovery/{vendor}_*.json
            vendor_items = list(base_path.glob(f"{name}_*.json"))
        
        elif base_path.name == "raw_specs":
            # storage/raw/raw_specs/{vendor}_openapi_*.yaml
            vendor_items = list(base_path.glob(f"{name}_openapi_*.*"))
        
        elif base_path.name in ["discovery", "normalized"]:
            # storage/discovery/{vendor}.json or storage/normalized/{vendor}/
            vendor_file = base_path / f"{name}.json"
            vendor_dir = base_path / name
            
            if vendor_file.exists():
                vendor_items.append(vendor_file)
            if vendor_dir.exists():
                vendor_items.append(vendor_dir)
        
        if vendor_items:
            storage_locations[str(base_path)] = vendor_items
    
    return storage_locations


# Remove vendor data from storage
def remove_vendor_storage(name: str, storage_locations: dict):

    print("\nRemoving vendor storage...")
    
    total_removed = 0
    
    for location, items in storage_locations.items():
        print(f"\n📁 {location}/")
        
        for item in items:
            try:
                if item.is_file():
                    item.unlink()
                    print(f"    Deleted file: {item.name}")
                    total_removed += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"    Deleted directory: {item.name}/")
                    total_removed += 1
            except Exception as e:
                print(f"    Failed to delete {item.name}: {e}")
    
    print(f"\n Removed {total_removed} storage item(s)")


# Interactive vendor removal workflow
def remove_vendor():

    print("\n" + "="*60)
    print("Remove Vendor from SpecWatch")
    print("="*60 + "\n")
    
    # Step 1: Get vendor name
    name = input("Vendor slug to remove (e.g., 'stripe'): ").strip().lower()
    
    if not name:
        print(" Vendor name cannot be empty")
        sys.exit(1)
    
    # Check if vendor exists
    if not vendor_exists(name):
        print(f" Vendor '{name}' not found in vendors.json")
        sys.exit(1)
    
    # Step 2: Find storage locations
    storage_locations = find_vendor_storage(name)
    
    # Show what will be removed
    print("\n" + "-"*60)
    print("The following will be removed:")
    print("-"*60)
    print("✓ Configuration files:")
    print("  - vendors.json")
    print("  - vendor_registry.json")
    print("  - vendor_specs.json (if present)")
    
    if storage_locations:
        print("\n✓ Storage locations (if --clean-storage is used):")
        for location, items in storage_locations.items():
            print(f"  📁 {location}/")
            for item in items[:3]:  # Show first 3 items
                print(f"     - {item.name}")
            if len(items) > 3:
                print(f"     ... and {len(items) - 3} more")
    else:
        print("\n  No storage data found for this vendor")
    
    print("-"*60)
    
    # Step 3: Confirm removal
    confirm = input(f"\nRemove vendor '{name}' from configuration? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print(" Cancelled")
        sys.exit(0)
    
    # Step 4: Ask about storage cleanup
    clean_storage = False
    if storage_locations:
        print("\n  WARNING: Storage cleanup will permanently delete:")
        print("   - Discovery results")
        print("   - Raw OpenAPI specs")
        print("   - Normalized snapshots")
        print("   - All historical data for this vendor")
        
        storage_confirm = input("\nAlso clean storage data? (y/N): ").strip().lower()
        clean_storage = (storage_confirm == 'y')
    
    # Step 5: Remove from config files
    print("\nRemoving vendor from configuration files...")
    
    try:
        removed = remove_from_vendors_json(name)
        
        if not removed:
            print(f" Failed to remove vendor from vendors.json")
            sys.exit(1)
        
        remove_from_vendor_registry(name)
        remove_from_vendor_specs(name)
        
        # Step 6: Clean storage if requested
        if clean_storage and storage_locations:
            remove_vendor_storage(name, storage_locations)
        elif storage_locations:
            print("\n  Storage data preserved (not deleted)")
            print("   To manually clean storage later:")
            print(f"   rm -rf storage/discovery/{name}.json")
            print(f"   rm -rf storage/raw/discovery/{name}_*.json")
            print(f"   rm -rf storage/raw/raw_specs/{name}_openapi_*")
            print(f"   rm -rf storage/normalized/{name}/")
        
        print("\n" + "="*60)
        print(f" Vendor '{name}' removed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n Error removing vendor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    remove_vendor()