"""
Diff Engine Pipeline - Compare normalized snapshots to detect API changes.

Args:
    vendors: List of vendors to process
    test_mode:  If test_mode is True, read from test/normalized_output/ and write to test/diff_output/
    Production Mode: If test_mode is False, read from storage/normalized/ and write to storage/diffs/
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from specwatch.diff.diff_engine import compute_diff
from specwatch.store.diff_store import store_diff
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Auto-discover vendors from input directory
def discover_vendors(input_dir: str) -> List[str]:

    base_path = Path(input_dir)
    
    if not base_path.exists():
        logger.warning(f"Input directory not found: {input_dir}")
        return []
    
    vendors = []
    
    for item in base_path.iterdir():
        if item.is_dir():
            # Check if vendor has baseline and latest files
            baseline = item / "baseline.json"
            latest = item / "latest.json"
            
            if baseline.exists() and latest.exists():
                vendors.append(item.name)
                logger.debug(f"Vendor discovered: {item.name}")
    
    return sorted(vendors)


# Run diff engine for a single vendor
def run_diff_for_vendor(
    vendor: str,
    input_dir: str,
    output_dir: str
) -> bool:

    logger.info(f"Running diff for {vendor}")
    
    # Build paths
    vendor_input = Path(input_dir) / vendor
    baseline_path = vendor_input / "baseline.json"
    latest_path = vendor_input / "latest.json"
    
    # Verify files exist
    if not baseline_path.exists():
        logger.error(f"Baseline not found: {baseline_path}")
        return False
    
    if not latest_path.exists():
        logger.error(f"Latest not found: {latest_path}")
        return False
    
    try:
        # Compute diff
        diff = compute_diff(
            baseline_path=str(baseline_path),
            latest_path=str(latest_path),
            vendor=vendor
        )
        
        # Store diff
        diff_path = store_diff(vendor, diff, output_dir=output_dir)
        
        # Log summary
        logger.info(
            f"Diff complete for {vendor}: "
            f"has_changes={diff.has_changes}, "
            f"endpoints_added={diff.summary.endpoints_added}, "
            f"endpoints_removed={diff.summary.endpoints_removed}, "
            f"endpoints_modified={diff.summary.endpoints_modified}, "
            f"endpoints_deprecated={diff.summary.endpoints_deprecated}"
        )
        
        if diff.summary.metadata_changes > 0:
            logger.warning(f"Metadata changes detected for {vendor}: {diff.summary.metadata_changes}")
        
        return True
        
    except Exception as e:
        logger.error(f"Diff failed for {vendor}: {e}", exc_info=True)
        return False


# Run diff pipeline for all specified vendors
def run_diff(
    vendors: Optional[List[str]] = None,
    test_mode: bool = False
) -> bool:

    # Determine input/output directories based on mode
    if test_mode:
        input_dir = "test/normalized_output"
        output_dir = "test/diff_output"
        mode_label = "TEST MODE"
    else:
        input_dir = "storage/normalized"
        output_dir = "storage/diffs"
        mode_label = "PRODUCTION MODE"
    
    logger.info(f"Diff pipeline started ({mode_label})")
    logger.info(f"Input: {input_dir}, Output: {output_dir}")
    
    # Auto-discover vendors if not specified
    if vendors is None:
        logger.info("Auto-discovering vendors...")
        vendors = discover_vendors(input_dir)
        
        if not vendors:
            logger.warning(f"No vendors found in {input_dir}")
            return False
        
        logger.info(f"Discovered vendors: {vendors}")
    
    # Process each vendor
    results = []
    
    for vendor in vendors:
        success = run_diff_for_vendor(vendor, input_dir, output_dir)
        results.append((vendor, success))
    
    # Summary
    successful = [v for v, s in results if s]
    failed = [v for v, s in results if not s]
    
    logger.info(
        f"Diff pipeline complete: "
        f"total={len(results)}, "
        f"successful={len(successful)}, "
        f"failed={len(failed)}"
    )
    
    if failed:
        logger.error(f"Failed vendors: {failed}")
    
    return len(failed) == 0


# For running diff pipeline standalone: python3 -m pipelines.diff_pipeline --test-mode
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run diff pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to process (e.g., stripe). If not specified, processes all."
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (uses test/normalized_output/ and test/diff_output/)"
    )
    
    args = parser.parse_args()
    
    success = run_diff(vendors=args.vendors, test_mode=args.test_mode)
    
    sys.exit(0 if success else 1)
