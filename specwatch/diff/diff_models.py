"""
Pydantic models for API diff structure.
Provides type-safe data structures for diff results.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# Represents a change to a single parameter
class ParameterChange(BaseModel):
    
    change_type: Literal[
        "parameter_added",
        "parameter_removed",
        "parameter_type_changed",
        "parameter_requirement_changed",
        "parameter_location_changed"
    ]
    parameter_name: str
    location: str  # path, query, header, body
    
    # Old/new values (None if added/removed)
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    
    # Specific field changes (for type/requirement changes)
    field_changed: Optional[str] = None  # e.g., "type", "required"
    old_field_value: Optional[Any] = None
    new_field_value: Optional[Any] = None


# Represents a change to an endpoint field (non-parameter)
class EndpointFieldChange(BaseModel):
    
    field_name: str  # e.g., "deprecated", "auth_required", "responses"
    old_value: Any
    new_value: Any


# Represents a change to an endpoint
class EndpointChange(BaseModel):
    
    change_type: Literal[
        "endpoint_added",
        "endpoint_removed",
        "endpoint_deprecated",
        "endpoint_modified"
    ]
    endpoint_id: str
    path: str
    method: str
    
    # For added/removed endpoints
    summary: Optional[str] = None
    
    # For modified endpoints
    parameter_changes: List[ParameterChange] = []
    field_changes: List[EndpointFieldChange] = []


# Represents a change to API metadata
class MetadataChange(BaseModel):
    
    field_name: str  # e.g., "base_url"
    old_value: Any
    new_value: Any


# Summary statistics of diff
class DiffSummary(BaseModel):
    
    endpoints_added: int = 0
    endpoints_removed: int = 0
    endpoints_modified: int = 0
    endpoints_deprecated: int = 0
    
    parameters_added: int = 0
    parameters_removed: int = 0
    parameters_modified: int = 0
    
    metadata_changes: int = 0


# Complete diff between two API snapshots
class APIDiff(BaseModel):
    
    vendor: str
    baseline_version: str  # Timestamp from baseline metadata
    latest_version: str    # Timestamp from latest metadata
    compared_at: str       # When diff was computed
    
    has_changes: bool
    summary: DiffSummary
    
    metadata_changes: List[MetadataChange] = []
    endpoint_changes: List[EndpointChange] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return self.model_dump(exclude_none=True)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return self.model_dump_json(indent=indent, exclude_none=True)
