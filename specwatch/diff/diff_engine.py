"""
Core diff engine for comparing API snapshots.
Compares baseline and latest normalized snapshots to detect changes.
"""

import json
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, List

from specwatch.utils.logger import get_logger
from .diff_models import (
    APIDiff,
    DiffSummary,
    EndpointChange,
    ParameterChange,
    MetadataChange,
    EndpointFieldChange
)
from .diff_utils import (
    build_endpoint_map,
    build_parameter_map,
    compare_parameter_fields,
    compare_endpoint_fields
)

logger = get_logger(__name__)


# Loads a normalized snapshot and returns snapshot data as dict
def load_snapshot(filepath: str) -> Dict[str, Any]:

    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {filepath}")
    
    with open(path, 'r') as f:
        return json.load(f)


# Compute diff between two normalized snapshots and returns APIDiff object containing all detected changes
def compute_diff(baseline_path: str, latest_path: str, vendor: str = None) -> APIDiff:

    logger.info(f"Computing diff: baseline={baseline_path}, latest={latest_path}")
    
    # Load snapshots
    baseline = load_snapshot(baseline_path)
    latest = load_snapshot(latest_path)
    
    # Extract vendor from metadata if not provided
    if vendor is None:
        vendor = baseline.get("metadata", {}).get("vendor", "unknown")
    
    # Extract versions
    baseline_version = baseline.get("metadata", {}).get("normalized_at", "unknown")
    latest_version = latest.get("metadata", {}).get("normalized_at", "unknown")
    
    logger.info(f"Comparing {vendor}: {baseline_version} → {latest_version}")
    
    # Initialize diff object
    diff = APIDiff(
        vendor=vendor,
        baseline_version=baseline_version,
        latest_version=latest_version,
        compared_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        has_changes=False,
        summary=DiffSummary()
    )
    
    # Compare metadata
    metadata_changes = _diff_metadata(baseline, latest)
    if metadata_changes:
        diff.metadata_changes = metadata_changes
        diff.summary.metadata_changes = len(metadata_changes)
    
    # Compare endpoints
    endpoint_changes = _diff_endpoints(
        baseline.get("endpoints", []),
        latest.get("endpoints", [])
    )
    
    if endpoint_changes:
        diff.endpoint_changes = endpoint_changes
        
        # Update summary
        for change in endpoint_changes:
            if change.change_type == "endpoint_added":
                diff.summary.endpoints_added += 1
            elif change.change_type == "endpoint_removed":
                diff.summary.endpoints_removed += 1
            elif change.change_type == "endpoint_deprecated":
                diff.summary.endpoints_deprecated += 1
            elif change.change_type == "endpoint_modified":
                diff.summary.endpoints_modified += 1
                
                # Count parameter changes
                for param_change in change.parameter_changes:
                    if "added" in param_change.change_type:
                        diff.summary.parameters_added += 1
                    elif "removed" in param_change.change_type:
                        diff.summary.parameters_removed += 1
                    else:
                        diff.summary.parameters_modified += 1
    
    # Determine if there are any changes
    diff.has_changes = (
        len(diff.metadata_changes) > 0 or
        len(diff.endpoint_changes) > 0
    )
    
    logger.info(
        f"Diff complete: has_changes={diff.has_changes}, "
        f"endpoints_added={diff.summary.endpoints_added}, "
        f"endpoints_removed={diff.summary.endpoints_removed}, "
        f"endpoints_modified={diff.summary.endpoints_modified}"
    )
    
    return diff


# Compares metadata between baseline and latest
def _diff_metadata(baseline: Dict[str, Any], latest: Dict[str, Any]) -> List[MetadataChange]:

    changes = []
    
    # Compare base_url (critical change)
    baseline_url = baseline.get("base_url", "")
    latest_url = latest.get("base_url", "")
    
    if baseline_url != latest_url:
        logger.info(f"Base URL changed: {baseline_url} → {latest_url}")
        changes.append(MetadataChange(
            field_name="base_url",
            old_value=baseline_url,
            new_value=latest_url
        ))
    
    return changes


# Compares endpoints between baseline and latest
def _diff_endpoints(
    baseline_endpoints: List[Dict[str, Any]],
    latest_endpoints: List[Dict[str, Any]]
) -> List[EndpointChange]:

    changes = []
    
    # Build endpoint maps by ID
    baseline_map = build_endpoint_map(baseline_endpoints)
    latest_map = build_endpoint_map(latest_endpoints)
    
    baseline_ids = set(baseline_map.keys())
    latest_ids = set(latest_map.keys())
    
    # Detect added endpoints
    added_ids = latest_ids - baseline_ids
    for endpoint_id in sorted(added_ids):
        endpoint = latest_map[endpoint_id]
        logger.info(f"Endpoint added: {endpoint_id}")
        
        changes.append(EndpointChange(
            change_type="endpoint_added",
            endpoint_id=endpoint_id,
            path=endpoint["path"],
            method=endpoint["method"],
            summary=endpoint.get("summary")
        ))
    
    # Detect removed endpoints
    removed_ids = baseline_ids - latest_ids
    for endpoint_id in sorted(removed_ids):
        endpoint = baseline_map[endpoint_id]
        logger.info(f"Endpoint removed: {endpoint_id}")
        
        changes.append(EndpointChange(
            change_type="endpoint_removed",
            endpoint_id=endpoint_id,
            path=endpoint["path"],
            method=endpoint["method"],
            summary=endpoint.get("summary")
        ))
    
    # Detect modified endpoints (common to both)
    common_ids = baseline_ids & latest_ids
    for endpoint_id in sorted(common_ids):
        baseline_endpoint = baseline_map[endpoint_id]
        latest_endpoint = latest_map[endpoint_id]
        
        # Check for deprecation change
        baseline_deprecated = baseline_endpoint.get("deprecated", False)
        latest_deprecated = latest_endpoint.get("deprecated", False)
        
        if not baseline_deprecated and latest_deprecated:
            logger.info(f"Endpoint deprecated: {endpoint_id}")
            changes.append(EndpointChange(
                change_type="endpoint_deprecated",
                endpoint_id=endpoint_id,
                path=latest_endpoint["path"],
                method=latest_endpoint["method"],
                field_changes=[EndpointFieldChange(
                    field_name="deprecated",
                    old_value=False,
                    new_value=True
                )]
            ))
        
        # Compare other endpoint fields
        field_changes_list = compare_endpoint_fields(baseline_endpoint, latest_endpoint)
        
        # Compare parameters
        parameter_changes = _diff_parameters(
            baseline_endpoint.get("parameters", []),
            latest_endpoint.get("parameters", [])
        )
        
        # If there are any changes (fields or parameters), record as modified
        if field_changes_list or parameter_changes:
            # Filter out deprecated changes
            field_changes_filtered = [
                EndpointFieldChange(field_name=field, old_value=old, new_value=new)
                for field, old, new in field_changes_list
                if field != "deprecated"
            ]
            
            if field_changes_filtered or parameter_changes:
                logger.info(
                    f"Endpoint modified: {endpoint_id} "
                    f"(field_changes={len(field_changes_filtered)}, "
                    f"param_changes={len(parameter_changes)})"
                )
                
                changes.append(EndpointChange(
                    change_type="endpoint_modified",
                    endpoint_id=endpoint_id,
                    path=latest_endpoint["path"],
                    method=latest_endpoint["method"],
                    field_changes=field_changes_filtered,
                    parameter_changes=parameter_changes
                ))
    
    return changes


# Compares parameters between baseline and latest endpoint
def _diff_parameters(
    baseline_params: List[Dict[str, Any]],
    latest_params: List[Dict[str, Any]]
) -> List[ParameterChange]:

    changes = []
    
    # Build parameter maps by (location, name)
    baseline_map = build_parameter_map(baseline_params)
    latest_map = build_parameter_map(latest_params)
    
    baseline_keys = set(baseline_map.keys())
    latest_keys = set(latest_map.keys())
    
    # Detect added parameters
    added_keys = latest_keys - baseline_keys
    for location, name in sorted(added_keys):
        param = latest_map[(location, name)]
        logger.debug(f"Parameter added: {location}:{name}")
        
        changes.append(ParameterChange(
            change_type="parameter_added",
            parameter_name=name,
            location=location,
            new_value=param
        ))
    
    # Detect removed parameters
    removed_keys = baseline_keys - latest_keys
    for location, name in sorted(removed_keys):
        param = baseline_map[(location, name)]
        logger.debug(f"Parameter removed: {location}:{name}")
        
        changes.append(ParameterChange(
            change_type="parameter_removed",
            parameter_name=name,
            location=location,
            old_value=param
        ))
    
    # Detect modified parameters (common to both)
    common_keys = baseline_keys & latest_keys
    for location, name in sorted(common_keys):
        baseline_param = baseline_map[(location, name)]
        latest_param = latest_map[(location, name)]
        
        # Compare parameter fields
        field_changes = compare_parameter_fields(baseline_param, latest_param)
        
        for field, old_value, new_value in field_changes:
            logger.debug(f"Parameter changed: {location}:{name}.{field}: {old_value} → {new_value}")
            
            # Determine specific change type
            if field == "type":
                change_type = "parameter_type_changed"
            elif field == "required":
                change_type = "parameter_requirement_changed"
            elif field == "location":
                change_type = "parameter_location_changed"
            else:
                # Generic change (description, etc)
                continue  # Skip non-critical changes for Phase 1
            
            changes.append(ParameterChange(
                change_type=change_type,
                parameter_name=name,
                location=location,
                old_value=baseline_param,
                new_value=latest_param,
                field_changed=field,
                old_field_value=old_value,
                new_field_value=new_value
            ))
    
    return changes
