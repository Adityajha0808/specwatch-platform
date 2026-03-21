"""
OpenAPI Normalization Orchestrator

Converts raw OpenAPI specs to canonical format.
Orchestrates parsing, extraction, and storage of normalized specs. Creates timestamped snapshot and updates baseline/latest symlinks.
"""

import os
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from specwatch.utils.logger import get_logger
from .parser import load_openapi_spec, validate_openapi_version, get_base_url
from .extractor import extract_endpoints

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0"

# Raised when normalization fails
class NormalizationError(Exception):
    pass


# Main Normalization function to normalize raw OpenAPI spec to canonical format
def normalize_spec(vendor: str, source_file: str) -> Dict[str, Any]:

    logger.info(f"Normalization started {vendor} {source_file}")
    
    try:
        # Step 1: Parse raw spec
        logger.info(f"Step parsing started {vendor}")
        spec = load_openapi_spec(source_file)
        logger.info(f"Spec loaded {vendor} keys {list(spec.keys())}")
        
        openapi_version = validate_openapi_version(spec)
        logger.info(f"OpenAPI version validated {vendor} {openapi_version}")
        
        # Step 2: Compute source hash
        logger.info(f"Step hashing started {vendor}")
        source_hash = _compute_file_hash(source_file)
        logger.info(f"Source hash computed {vendor} {source_hash}")
        
        # Step 3: Extract base URL
        logger.info(f"Step base url extraction started {vendor}")
        base_url = get_base_url(spec)
        logger.info(f"Base URL extracted {vendor} {base_url}")
        
        # Step 4: Extract endpoints
        logger.info(f"Step endpoints extraction started {vendor}")
        endpoints = extract_endpoints(spec)
        logger.info(f"Endpoints extracted {vendor} count {len(endpoints)}")
        
        # Step 5: Build canonical format
        logger.info(f"Building canonical format {vendor}")
        canonical = {
            "metadata": {
                "vendor": vendor,
                "normalized_at": datetime.utcnow().isoformat() + "Z",
                "source_file": str(Path(source_file).name),
                "source_hash": source_hash,
                "schema_version": SCHEMA_VERSION,
                "openapi_version": openapi_version
            },
            "base_url": base_url,
            "endpoints": endpoints
        }
        
        logger.info(f"Normalization complete {vendor} endpoints {len(endpoints)}")
        
        return canonical
        
    except Exception as e:
        logger.error(f"Normalization failed {vendor} {source_file} error {str(e)} type {type(e).__name__}")
        raise NormalizationError(f"Failed to normalize {vendor}: {e}")


# Normalize and store to filesystem with versioning
def normalize_and_store(vendor: str, source_file: str, output_dir: str = "storage/normalized") -> str:

    logger.info(f"normalize_and_store_started. Vendor={vendor}, source_file={source_file}")
    
    # Compute source hash BEFORE normalization (for deduplication)
    source_hash = _compute_file_hash(source_file)
    logger.debug(f"source_hash_computed. Vendor={vendor}, hash={source_hash}")
    
    # Check if latest snapshot has same hash (DEDUPLICATION). Skips normalization if source hash matches latest snapshot.
    latest_link = Path(output_dir) / vendor / "latest.json"
    if latest_link.exists():
        try:
            with open(latest_link) as f:
                latest_data = json.load(f)
                latest_hash = latest_data.get('metadata', {}).get('source_hash')
                latest_schema_version = latest_data.get('metadata', {}).get('schema_version')
            
            # Checking both hash AND schema version
            if latest_hash == source_hash and latest_schema_version == SCHEMA_VERSION:
                logger.info(f"normalization_skipped, vendor={vendor}, reason=source_and_schema_unchanged, hash={source_hash}, schema={SCHEMA_VERSION}")
                return str(latest_link.resolve())  # Return existing snapshot path
            elif latest_hash == source_hash:
                logger.info(f"re_normalizing_for_schema_upgrade, old_schema={latest_schema_version}, new_schema={SCHEMA_VERSION}")
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"failed_to_read_latest, vendor={vendor}, error={str(e)}")
    
    # Hash is different or no latest snapshot → proceed with normalization
    logger.debug(f"proceeding_with_normalization, vendor={vendor}, reason=source_changed_or_new")
    
    # Step 1: Normalize
    logger.debug(f"calling_normalize_spec, vendor={vendor}")
    canonical = normalize_spec(vendor, source_file)
    
    # Step 2: Determine paths
    logger.debug(f"determining_output_path, vendor={vendor}, output_dir={output_dir}")
    timestamp = _extract_timestamp_from_filename(source_file)
    
    # Create snapshots directory structure
    vendor_dir = Path(output_dir) / vendor
    snapshots_dir = vendor_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Path for timestamped snapshot
    snapshot_path = snapshots_dir / f"{timestamp}.json"
    
    logger.debug(f"output_path_determined, vendor={vendor}, timestamp={timestamp}, snapshot_path={str(snapshot_path)}")
    
    # Step 3: Store timestamped snapshot
    logger.debug(f"writing_snapshot, snapshot_path={str(snapshot_path)}")
    with open(snapshot_path, 'w') as f:
        json.dump(canonical, f, indent=2, sort_keys=True)
    
    file_size = snapshot_path.stat().st_size
    logger.info(f"snapshot_stored, vendor={vendor}, snapshot_path={str(snapshot_path)}, file_size_bytes={file_size}, file_size_kb={round(file_size / 1024, 2)}")
    
    # Step 4: Update 'latest.json' symlink
    latest_link = vendor_dir / "latest.json"
    _update_symlink(latest_link, snapshot_path)
    
    logger.info(f"latest_link_updated, vendor={vendor}, latest_link={str(latest_link)}")
    
    # Step 5: Create 'baseline.json' if it doesn't exist
    baseline_link = vendor_dir / "baseline.json"
    if not baseline_link.exists():
        _update_symlink(baseline_link, snapshot_path)
        logger.info(f"baseline_created, vendor={vendor}, baseline_link={str(baseline_link)}")
    else:
        logger.debug(f"baseline_already_exists, vendor={vendor}, baseline_link={str(baseline_link)}")
    
    return str(snapshot_path)


# Update or create symlink
def _update_symlink(link_path: Path, target_path: Path):
    
    logger.debug(f"updating_symlink, link={str(link_path)}, target={str(target_path)}")
    
    # Remove existing symlink if it exists
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
        logger.debug(f"existing_symlink_removed, link={str(link_path)}")
    
    # Create relative symlink
    relative_target = os.path.relpath(target_path, link_path.parent)
    link_path.symlink_to(relative_target)
    
    logger.debug(f"symlink_created, link={str(link_path)}, target={relative_target}")


# Compute SHA256 hash of file
def _compute_file_hash(filepath: str) -> str:

    logger.info(f"Computing file hash {filepath}")
    
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        content = f.read()
        hasher.update(content)
    
    full_hash = hasher.hexdigest()
    short_hash = full_hash[:16]
    
    logger.info(f"File hash computed {filepath} {short_hash}")
    
    return short_hash


# Extract timestamp from filename
def _extract_timestamp_from_filename(filepath: str) -> str:

    logger.info(f"Extracting timestamp from filename {filepath}")
    
    filename = Path(filepath).stem
    logger.info(f"Filename stem {filename}")
    
    parts = filename.split('_')
    logger.info(f"Filename parts {parts}")
    
    for part in reversed(parts):
        if 'T' in part or '-' in part:
            logger.info(f"Timestamp found in filename {part}")
            return part
    
    fallback_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.warning(f"Timestamp extraction failed {filepath} using fallback {fallback_timestamp}")
    
    return fallback_timestamp
