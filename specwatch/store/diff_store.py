"""
Storage layer for diff results.
Handles storing and retrieving diff results for both test and production modes.
Storage: Base directory for diffs, "storage/diffs" for production, "test/diff_output" for testing
"""


import json
from pathlib import Path
from typing import Optional

from specwatch.utils.logger import get_logger
from specwatch.diff.diff_models import APIDiff

logger = get_logger(__name__)


# Stores diff result to filesystem and returns the path
def store_diff(vendor: str, diff: APIDiff, output_dir: str = "storage/diffs") -> str:

    logger.info(f"Storing diff for {vendor} to {output_dir}")
    
    # Build filename from versions
    baseline_ts = diff.baseline_version.replace(":", "-").replace("T", "T")
    latest_ts = diff.latest_version.replace(":", "-").replace("T", "T")
    filename = f"diff_{baseline_ts}_to_{latest_ts}.json"
    
    # Create vendor directory
    vendor_dir = Path(output_dir) / vendor
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    # Full path
    diff_path = vendor_dir / filename
    
    # Store diff
    with open(diff_path, 'w') as f:
        f.write(diff.to_json(indent=2))
    
    logger.info(f"Diff stored: {diff_path}, has_changes={diff.has_changes}")
    
    return str(diff_path)


# Loads a diff result from filesystem
def load_diff(vendor: str, filename: str, output_dir: str = "storage/diffs") -> Optional[APIDiff]:

    diff_path = Path(output_dir) / vendor / filename
    
    if not diff_path.exists():
        logger.warning(f"Diff not found: {diff_path}")
        return None
    
    with open(diff_path, 'r') as f:
        data = json.load(f)
    
    return APIDiff(**data)


# Get the most recent diff for a vendor
def get_latest_diff(vendor: str, output_dir: str = "storage/diffs") -> Optional[APIDiff]:

    vendor_dir = Path(output_dir) / vendor
    
    if not vendor_dir.exists():
        return None
    
    # Find all diff files
    diff_files = sorted(vendor_dir.glob("diff_*.json"), reverse=True)
    
    if not diff_files:
        return None
    
    # Return most recent
    latest = diff_files[0]
    return load_diff(vendor, latest.name, output_dir)
