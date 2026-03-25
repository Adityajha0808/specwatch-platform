"""
Pydantic models for LLM classification results.
Defines type-safe structures for change classifications.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# Classification result for a single change
class ChangeClassification(BaseModel):
    
    severity: Literal["breaking", "deprecation", "additive", "minor"]
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    reasoning: str
    recommended_action: Literal[
        "alert_critical",      # Breaking → Slack alert
        "alert_warning",       # Deprecation → GitHub issue
        "notify_info",         # Additive → Info log
        "ignore"               # Minor → No action
    ]
    migration_path: Optional[str] = None
    estimated_impact: Literal["high", "medium", "low"]


# Endpoint change with LLM classification
class ClassifiedEndpointChange(BaseModel):
    
    # Original change data
    change_type: str
    endpoint_id: str
    path: str
    method: str
    
    # LLM classification
    classification: ChangeClassification
    
    # Original change details
    details: Dict[str, Any] = {}


# Summary of classifications
class ClassificationSummary(BaseModel):
    
    total_changes: int = 0
    breaking_changes: int = 0
    deprecations: int = 0
    additive_changes: int = 0
    minor_changes: int = 0
    
    critical_alerts_needed: int = 0
    warning_alerts_needed: int = 0
    info_notifications: int = 0


# Complete diff with LLM classifications
class ClassifiedAPIDiff(BaseModel):
    
    vendor: str
    baseline_version: str
    latest_version: str
    classified_at: str
    
    # Original diff summary
    diff_summary: Dict[str, Any]
    
    # Classified changes
    classified_changes: List[ClassifiedEndpointChange] = []
    
    # Classification summary
    classification_summary: ClassificationSummary
    
    # Quick flags
    has_breaking_changes: bool = False
    has_deprecations: bool = False
    requires_immediate_action: bool = False
    
    # Convert to dict for JSON serialization
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
    
    # Convert to JSON string
    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent, exclude_none=True)
