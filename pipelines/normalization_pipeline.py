"""
Normalization Pipeline - Convert raw OpenAPI specs to canonical format.

Args:
    Vendors: List of vendor names to normalize. If None, normalizes all.
        
Returns:
    True if all normalizations successful, False otherwise.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple

from specwatch.normalization.normalizer import normalize_and_store, NormalizationError
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Main normalization pipeline entry point
def run_normalization(vendors: List[str] = None) -> bool:
    
    logger.info("Normalization pipeline started")
    
    # Default to all vendors if not specified
    if vendors is None:
        logger.info("Discovering vendors")
        vendors = _discover_vendors()
        logger.info(f"Vendors discovered: {len(vendors)}")
    
    if not vendors:
        logger.warning("No raw specs available for normalization")
        return False
    
    results = []
    
    for vendor in vendors:
        logger.info(f"Processing vendor start {vendor}")
        
        try:
            success = _normalize_vendor(vendor)
            results.append((vendor, success))
            
            if success:
                logger.info("Vendor normalized success")
            else:
                logger.warning("Vendor normalization failed")
                
        except Exception as e:
            logger.error(f"Vendor normalization exception {str(e)}")
            results.append((vendor, False))
    
    # Summary
    successful = [v for v, s in results if s]
    failed = [v for v, s in results if not s]
    
    logger.info(f"Normalization pipeline complete. Total: {len(results)}. Successful: {len(successful)}. Failed: {len(failed)}")
    
    return len(failed) == 0


# Normalize latest raw spec for a single vendor
def _normalize_vendor(vendor: str) -> bool:

    logger.debug(f"normalize_vendor_started={vendor}")
    
    # Find latest raw spec for this vendor
    raw_dir = Path("storage/raw/raw_specs")
    logger.debug(f"Searching_raw_specs for {vendor} :, {str(raw_dir)}")
    
    # Look for vendor-specific files (supports both .yaml and .json)
    yaml_files = list(raw_dir.glob(f"{vendor}_openapi_*.yaml"))
    json_files = list(raw_dir.glob(f"{vendor}_openapi_*.json"))
    
    logger.debug(f"raw_specs_search_result {vendor}, {len(yaml_files)}, {len(json_files)}")
    
    spec_files = sorted(yaml_files + json_files, reverse=True)
    
    if not spec_files:
        logger.warning("No raw spec found")
        return False
    
    latest_spec = spec_files[0]
    logger.info("Found raw spec")
    
    try:
        logger.info("Calling normalize and store")
        output_path = normalize_and_store(vendor, str(latest_spec))
        logger.info("Normalization stored")
        
        # Validate output was created
        if not Path(output_path).exists():
            logger.error(f"Output file missing for {vendor}")
            return False
        
        output_size = Path(output_path).stat().st_size
        logger.info("Output file validated")
        
        return True
        
    except NormalizationError as e:
        logger.error(f"Normalization error: {str(e)}")
        return False


# Auto-discover vendors from raw specs directory
def _discover_vendors() -> List[str]:

    logger.info("Discovering vendors from filesystem")
    
    raw_dir = Path("storage/raw/raw_specs")
    
    if not raw_dir.exists():
        logger.warning("Raw directory not found")
        return []
    
    vendors = set()
    
    # Extract vendor names from filenames (e.g., "stripe_openapi_*.yaml" -> "stripe")
    file_count = 0
    for spec_file in raw_dir.glob("*_openapi_*"):
        file_count += 1
        parts = spec_file.stem.split('_')
        
        if len(parts) >= 2:
            vendor = parts[0]  # First part is vendor name
            vendors.add(vendor)
            logger.info(f"Vendor discovered {vendor}")
    
    vendor_list = sorted(list(vendors))
    
    logger.info(f"Vendor discovery complete. Total_files_scanned={file_count}, unique_vendors={len(vendor_list)}, vendors={vendor_list}")
    
    return vendor_list


# For Running normalization pipeline standalone
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run normalization pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to normalize (e.g., stripe twilio). If not specified, normalizes all."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Enable debug logging if requested
    if args.debug:
        import os
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    logger.info("Normalization pipeline cli started")
    
    success = run_normalization(vendors=args.vendors)
    
    logger.info("Normalization pipeline cli complete")
    sys.exit(0 if success else 1)
