"""
Storage layer for classified diff results.
Handles storing and retrieving classified diffs for both test and production modes.
"""

import json
from pathlib import Path
from typing import Optional

from specwatch.utils.logger import get_logger
from specwatch.classification.classification_models import ClassifiedAPIDiff

logger = get_logger(__name__)


# Store classified diff result to filesystem
def store_classified_diff(
    vendor: str,
    classified_diff: ClassifiedAPIDiff,
    output_dir: str = "storage/classified_diffs"
) -> str:

    logger.info(f"Storing classified diff for {vendor} to {output_dir}")
    
    # Build filename from versions
    baseline_ts = classified_diff.baseline_version.replace(":", "-").replace("T", "T")
    latest_ts = classified_diff.latest_version.replace(":", "-").replace("T", "T")
    filename = f"classified_diff_{baseline_ts}_to_{latest_ts}.json"
    
    # Create vendor directory
    vendor_dir = Path(output_dir) / vendor
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    # Full path
    output_path = vendor_dir / filename
    
    # Store classified diff
    with open(output_path, 'w') as f:
        f.write(classified_diff.to_json(indent=2))
    
    logger.info(
        f"Classified diff stored: {output_path}, "
        f"breaking={classified_diff.classification_summary.breaking_changes}, "
        f"deprecations={classified_diff.classification_summary.deprecations}"
    )
    
    return str(output_path)


# Load a classified diff from filesystem
def load_classified_diff(
    vendor: str,
    filename: str,
    output_dir: str = "storage/classified_diffs"
) -> Optional[ClassifiedAPIDiff]:
    
    file_path = Path(output_dir) / vendor / filename
    
    if not file_path.exists():
        logger.warning(f"Classified diff not found: {file_path}")
        return None
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return ClassifiedAPIDiff(**data)


# Get the most recent classified diff for a vendor
def get_latest_classified_diff(
    vendor: str,
    output_dir: str = "storage/classified_diffs"
) -> Optional[ClassifiedAPIDiff]:
    
    vendor_dir = Path(output_dir) / vendor
    
    if not vendor_dir.exists():
        return None
    
    # Find all classified diff files
    classified_files = sorted(
        vendor_dir.glob("classified_diff_*.json"),
        reverse=True
    )
    
    if not classified_files:
        return None
    
    # Return most recent
    latest = classified_files[0]
    return load_classified_diff(vendor, latest.name, output_dir)
