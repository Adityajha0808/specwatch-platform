import json
from pathlib import Path

CONFIG_PATH = Path("specwatch/config/json/vendors.json")


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("vendors.json not found")

    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def vendor_exists(config, name):
    for v in config["vendors"]:
        if v["name"] == name:
            return True
    return False


# Add new Vendor
def add_vendor():

    config = load_config()

    print("\n--- Add New Vendor ---")

    name = input("Vendor slug (example: stripe): ").strip()
    display_name = input("Display name (example: Stripe): ").strip()

    if vendor_exists(config, name):
        print("Vendor already exists.")
        return

    domains = input(
        "Trusted domains (comma separated): "
    ).split(",")

    domains = [d.strip() for d in domains]

    docs_query = input("Docs search query: ")
    openapi_query = input("OpenAPI search query: ")
    changelog_query = input("Changelog search query: ")

    vendor = {
        "name": name,
        "display_name": display_name,
        "trusted_domains": domains,
        "queries": {
            "docs": docs_query,
            "openapi": openapi_query,
            "changelog": changelog_query
        }
    }

    config["vendors"].append(vendor)

    save_config(config)

    print(f"\nVendor '{display_name}' added successfully.")


# Run "python scripts/add_vendor.py" to add a new vendor
if __name__ == "__main__":
    add_vendor()
