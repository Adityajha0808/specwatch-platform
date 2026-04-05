#!/usr/bin/env python3
"""
Classification Pipeline - LLM-based classification of API changes by severity and impact.

Supports two modes:
- Test mode: Uses test diffs from test/diff_output/
- Production mode: Uses real diffs from storage/diffs/
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional
from datetime import datetime, UTC

from specwatch.classification.classifier import ChangeClassifier
from specwatch.diff.diff_models import APIDiff
from specwatch.store.classification_store import store_classified_diff
from specwatch.utils.logger import get_logger

from specwatch.classification.classification_models import (
    ClassifiedAPIDiff,
    ClassificationSummary
)

logger = get_logger(__name__)


# Auto-discover vendors from diff directory
def discover_vendors_from_diffs(diff_dir: str) -> List[str]:

    base_path = Path(diff_dir)
    
    if not base_path.exists():
        logger.warning(f"Diff directory not found: {diff_dir}")
        return []
    
    vendors = []
    
    for item in base_path.iterdir():
        if item.is_dir():
            # Check if vendor has diff files
            diff_files = list(item.glob("diff_*.json"))
            
            if diff_files:
                vendors.append(item.name)
                logger.debug(f"Vendor discovered: {item.name}")
    
    return sorted(vendors)


# Load the most recent diff for a vendor
def load_latest_diff(vendor: str, diff_dir: str) -> Optional[APIDiff]:

    vendor_dir = Path(diff_dir) / vendor
    
    if not vendor_dir.exists():
        logger.warning(f"Vendor diff directory not found: {vendor_dir}")
        return None
    
    # Find all diff files
    diff_files = sorted(vendor_dir.glob("diff_*.json"), reverse=True)
    
    if not diff_files:
        logger.warning(f"No diff files found for {vendor}")
        return None
    
    # Load most recent
    latest_diff_path = diff_files[0]
    logger.info(f"Loading diff: {latest_diff_path}")
    
    with open(latest_diff_path, 'r') as f:
        data = json.load(f)
    
    return APIDiff(**data)


# Classify all changes for a single vendor
def classify_vendor(
    vendor: str,
    diff_dir: str,
    output_dir: str,
    classifier: ChangeClassifier
) -> bool:
    
    logger.info(f"Classifying changes for {vendor}")
    
    # Load latest diff
    diff = load_latest_diff(vendor, diff_dir)
    
    if not diff:
        logger.error(f"No diff found for {vendor}")
        return False
    
    # Check if there are changes to classify
    if not diff.has_changes:
        logger.info(f"No changes detected for {vendor}, skipping classification")

        # Still store empty classification for audit trail
        empty_classified = ClassifiedAPIDiff(
            vendor=vendor,
            baseline_version=diff.baseline_version,
            latest_version=diff.latest_version,
            classified_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S') + "Z",
            diff_summary=diff.summary.model_dump(),
            classified_changes=[],
            classification_summary=ClassificationSummary(),
            has_breaking_changes=False,
            has_deprecations=False,
            requires_immediate_action=False
        )
        
        store_classified_diff(vendor, empty_classified, output_dir)
        return True
    
    try:
        # Classify diff
        logger.info(f"Classifying {len(diff.endpoint_changes)} changes for {vendor}")
        classified_diff = classifier.classify_diff(diff)
        
        # Store result
        output_path = store_classified_diff(vendor, classified_diff, output_dir)
        
        # Log summary
        summary = classified_diff.classification_summary
        logger.info(
            f"Classification complete for {vendor}: "
            f"breaking={summary.breaking_changes}, "
            f"deprecations={summary.deprecations}, "
            f"additive={summary.additive_changes}, "
            f"minor={summary.minor_changes}"
        )
        
        if classified_diff.requires_immediate_action:
            logger.warning(
                f"CRITICAL: {vendor} has {summary.critical_alerts_needed} "
                f"breaking change(s) requiring immediate action!"
            )
        
        if classified_diff.has_deprecations:
            logger.warning(
                f"WARNING: {vendor} has {summary.deprecations} "
                f"deprecation(s) requiring migration planning"
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Classification failed for {vendor}: {e}", exc_info=True)
        return False


# Run classification pipeline for specified vendors
def run_classification(
    vendors: Optional[List[str]] = None,
    test_mode: bool = False
) -> bool:
    
    # Determine input/output directories based on mode
    if test_mode:
        diff_dir = "test/diff_output"
        output_dir = "test/classified_output"
        mode_label = "TEST MODE"
    else:
        diff_dir = "storage/diffs"
        output_dir = "storage/classified_diffs"
        mode_label = "PRODUCTION MODE"
    
    logger.info(f"Classification pipeline started ({mode_label})")
    logger.info(f"Input: {diff_dir}, Output: {output_dir}")
    
    # Initialize classifier
    try:
        classifier = ChangeClassifier()
        logger.info(f"Classifier initialized with model: {classifier.model}")
    except ValueError as e:
        logger.error(f"Failed to initialize classifier: {e}")
        logger.error("Make sure GROQ_API_KEY is set in .env file")
        return False
    
    # Auto-discover vendors if not specified
    if vendors is None:
        logger.info("Auto-discovering vendors...")
        vendors = discover_vendors_from_diffs(diff_dir)
        
        if not vendors:
            logger.warning(f"No vendors found in {diff_dir}")
            return False
        
        logger.info(f"Discovered vendors: {vendors}")
    
    # Process each vendor
    results = []
    
    for vendor in vendors:
        success = classify_vendor(vendor, diff_dir, output_dir, classifier)
        results.append((vendor, success))
    
    # Summary
    successful = [v for v, s in results if s]
    failed = [v for v, s in results if not s]
    
    logger.info(
        f"Classification pipeline complete: "
        f"total={len(results)}, "
        f"successful={len(successful)}, "
        f"failed={len(failed)}"
    )
    
    if failed:
        logger.error(f"Failed vendors: {failed}")
    
    return len(failed) == 0


# For running classification pipeline standalone: python3 -m pipelines.classification_pipeline --test-mode
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run LLM classification pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to process (e.g., stripe). If not specified, processes all."
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (uses test/diff_output/ and test/classified_output/)"
    )
    
    args = parser.parse_args()
    
    success = run_classification(vendors=args.vendors, test_mode=args.test_mode)
    
    sys.exit(0 if success else 1)
