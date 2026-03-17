import json
from pathlib import Path
from specwatch.config.config_validator import validate_configs

BASE_PATH = Path("specwatch/config")

VENDORS_FILE = BASE_PATH / "json/vendors.json"
REGISTRY_FILE = BASE_PATH / "json/vendor_registry.json"
QUERIES_FILE = BASE_PATH / "json/discovery_queries.json"


def load_all_configs():

    vendors = load_vendors()
    registry = load_vendor_registry()
    queries = load_queries()

    validate_configs(vendors, registry, queries)

    return vendors, registry, queries


def load_json(path):

    with open(path, "r") as f:
        return json.load(f)


def load_vendors():

    data = load_json(VENDORS_FILE)
    return data["vendors"]


def load_vendor_registry():

    return load_json(REGISTRY_FILE)["vendors"]


def load_queries():

    return load_json(QUERIES_FILE)["queries"]
