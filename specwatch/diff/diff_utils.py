"""
Utility functions for diff engine.
Provides helper functions for endpoint/parameter mapping and comparison.
"""

from typing import Dict, List, Tuple, Any

""" Build a map of endpoints by their ID for O(1) lookup.
    
    Args:
        endpoints: List of endpoint dicts from normalized snapshot
        
    Returns:
        Dict mapping endpoint_id → endpoint dict
        
    Example:
        {
            "POST:/v1/customers": {...},
            "GET:/v1/customers": {...}
        }
"""
def build_endpoint_map(endpoints: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {endpoint["id"]: endpoint for endpoint in endpoints}


""" Build a map of parameters by (location, name) for O(1) lookup.
    
    Args:
        parameters: List of parameter dicts from endpoint
        
    Returns:
        Dict mapping (location, name) → parameter dict
        
    Example:
        {
            ("body", "email"): {"name": "email", "type": "string", ...},
            ("query", "limit"): {"name": "limit", "type": "integer", ...}
        }
"""
def build_parameter_map(parameters: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    
    return {
        (param["location"], param["name"]): param
        for param in parameters
    }


""" Compare two parameter dicts and find changed fields.
    
    Args:
        old_param: Parameter from baseline
        new_param: Parameter from latest
        
    Returns:
        List of (field_name, old_value, new_value) tuples for changed fields
        
    Example:
        [("type", "string", "integer"), ("required", false, true)]
"""
def compare_parameter_fields(
    old_param: Dict[str, Any],
    new_param: Dict[str, Any]
) -> List[Tuple[str, Any, Any]]:

    changes = []
    
    # Fields to compare
    fields_to_check = ["type", "required", "location", "description"]
    
    for field in fields_to_check:
        old_value = old_param.get(field)
        new_value = new_param.get(field)
        
        if old_value != new_value:
            changes.append((field, old_value, new_value))
    
    return changes


""" Compare two endpoint dicts and find changed fields (excluding parameters).
    
    Args:
        old_endpoint: Endpoint from baseline
        new_endpoint: Endpoint from latest
        
    Returns:
        List of (field_name, old_value, new_value) tuples for changed fields
        
    Example:
        [("deprecated", false, true), ("auth_required", true, false)]
"""
def compare_endpoint_fields(
    old_endpoint: Dict[str, Any],
    new_endpoint: Dict[str, Any]
) -> List[Tuple[str, Any, Any]]:
    
    changes = []
    
    # Fields to compare (excluding parameters which are handled separately)
    fields_to_check = [
        "deprecated",
        "auth_required",
        "request_body_required",
        "summary",
        "responses"
    ]
    
    for field in fields_to_check:
        old_value = old_endpoint.get(field)
        new_value = new_endpoint.get(field)
        
        # Special handling for responses (array comparison)
        if field == "responses":
            if set(old_value or []) != set(new_value or []):
                changes.append((field, old_value, new_value))
        else:
            if old_value != new_value:
                changes.append((field, old_value, new_value))
    
    return changes


""" Heuristic to determine if a change is potentially breaking.
    
    Rule-based classifier; LLM will be used for more sophisticated classification.
    
    Args:
        change_type: Type of change
        details: Additional details about the change
        
    Returns:
        True if potentially breaking, False otherwise
"""
def is_breaking_change(change_type: str, details: Dict[str, Any] = None) -> bool:

    # Endpoint-level breaking changes
    if change_type == "endpoint_removed":
        return True
    
    if change_type == "endpoint_added":
        return False
    
    if change_type == "endpoint_deprecated":
        return False  # Warning, not immediately breaking
    
    # Parameter-level breaking changes
    if change_type == "parameter_removed":
        return True  # Clients might be sending it
    
    if change_type == "parameter_added":
        # Only breaking if required
        if details and details.get("new_value", {}).get("required"):
            return True
        return False
    
    if change_type == "parameter_type_changed":
        return True  # Type mismatch
    
    if change_type == "parameter_requirement_changed":
        # Only breaking if optional → required
        if details:
            old_required = details.get("old_value")
            new_required = details.get("new_value")
            if not old_required and new_required:
                return True
        return False
    
    # Default: not breaking
    return False


""" Format parameter key for display.
    
    Args:
        location: Parameter location (path, query, header, body)
        name: Parameter name
        
    Returns:
        Formatted string like "body:email" or "query:limit"
"""
def format_parameter_key(location: str, name: str) -> str:
    return f"{location}:{name}"
