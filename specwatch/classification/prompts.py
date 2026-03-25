"""
LLM prompt templates for API change classification.
Builds prompts that provide context and classification schema to the LLM.
"""

import json
from typing import Dict, Any, List
from specwatch.diff.diff_models import EndpointChange, APIDiff


# Build classification prompt for LLM
def build_classification_prompt(
    change: EndpointChange,
    full_diff: APIDiff
) -> str:
    
    # Extract other changes for context
    other_changes = []
    for c in full_diff.endpoint_changes:
        if c.endpoint_id != change.endpoint_id:
            other_changes.append({
                "change_type": c.change_type,
                "endpoint_id": c.endpoint_id,
                "path": c.path,
                "method": c.method
            })
    
    other_changes_str = json.dumps(other_changes, indent=2) if other_changes else "None"
    
    # Build change details
    change_details = {
        "change_type": change.change_type,
        "endpoint_id": change.endpoint_id,
        "path": change.path,
        "method": change.method,
        "summary": change.summary if hasattr(change, 'summary') and change.summary else None
    }
    
    # Add parameter changes if present
    if change.parameter_changes:
        change_details["parameter_changes"] = [
            {
                "change_type": pc.change_type,
                "parameter_name": pc.parameter_name,
                "location": pc.location,
                "field_changed": pc.field_changed,
                "old_field_value": pc.old_field_value,
                "new_field_value": pc.new_field_value
            }
            for pc in change.parameter_changes
        ]
    
    # Add field changes if present
    if change.field_changes:
        change_details["field_changes"] = [
            {
                "field_name": fc.field_name,
                "old_value": fc.old_value,
                "new_value": fc.new_value
            }
            for fc in change.field_changes
        ]
    
    prompt = f"""You are an API versioning expert analyzing API changes for breaking compatibility issues.

            # API Context
            
            **Vendor**: {full_diff.vendor}
            **Baseline Version**: {full_diff.baseline_version}
            **Latest Version**: {full_diff.latest_version}
            
            # Change to Classify
            
            {json.dumps(change_details, indent=2)}
            
            # Other Changes in This Diff
            
            {other_changes_str}
            
            # Your Task
            
            Classify this API change and return a JSON object with the following structure:
            
            {{
              "severity": "breaking" | "deprecation" | "additive" | "minor",
              "confidence": <float between 0.0 and 1.0>,
              "reasoning": "<detailed explanation>",
              "recommended_action": "alert_critical" | "alert_warning" | "notify_info" | "ignore",
              "migration_path": "<how to migrate, or null if not applicable>",
              "estimated_impact": "high" | "medium" | "low"
            }}
            
            # Classification Guidelines
            
            **Breaking Changes** (severity: "breaking", action: "alert_critical"):
            - Endpoint removed (existing clients will get 404)
            - Required parameter added (old clients missing it will fail)
            - Parameter type changed (type mismatch errors)
            - Optional parameter made required (old clients don't send it)
            - Base URL changed (all requests go to wrong location)
            - Auth requirement added where there was none (unauthorized errors)
            
            **Deprecation** (severity: "deprecation", action: "alert_warning"):
            - Endpoint marked deprecated but still functional
            - Will break in future, but works now
            - Gives teams time to migrate
            
            **Additive Changes** (severity: "additive", action: "notify_info"):
            - New endpoint added (backward compatible)
            - Optional parameter added (clients can ignore it)
            - Required parameter made optional (more permissive)
            - New response status code added for informational purposes
            
            **Minor Changes** (severity: "minor", action: "ignore"):
            - Description/documentation changed
            - Summary text updated
            - Non-functional metadata changes
            
            # Confidence Scale
            
            - 1.0: Certain (e.g., endpoint removed is definitely breaking)
            - 0.9: Very confident (clear breaking change with minor ambiguity)
            - 0.7-0.8: Confident (likely breaking based on API best practices)
            - 0.5-0.6: Moderate (depends on client implementation)
            - 0.3-0.4: Low confidence (need more context)
            
            # Context Analysis
            
            Consider:
            1. Are there replacement endpoints? (e.g., charges → payment_intents)
            2. Is this part of a documented migration path?
            3. What's the typical impact on API consumers?
            4. Is there a grace period implied by deprecation?
            
            # Response Format
            
            Return ONLY valid JSON. No markdown, no code fences, no additional text.
            Do not wrap the JSON in ```json blocks.
        """
    
    return prompt


# Build fallback classification using heuristics when LLM classification fails
def build_fallback_classification(change: EndpointChange) -> Dict[str, Any]:
    
    # Simple heuristic rules
    if change.change_type == "endpoint_removed":
        return {
            "severity": "breaking",
            "confidence": 0.95,
            "reasoning": "Endpoint removal causes existing clients to receive 404 errors. [Heuristic classification]",
            "recommended_action": "alert_critical",
            "migration_path": "Check vendor documentation for replacement endpoint.",
            "estimated_impact": "high"
        }
    
    elif change.change_type == "endpoint_deprecated":
        return {
            "severity": "deprecation",
            "confidence": 0.9,
            "reasoning": "Endpoint marked as deprecated. Still functional but scheduled for removal. [Heuristic classification]",
            "recommended_action": "alert_warning",
            "migration_path": "Plan migration before deprecation deadline.",
            "estimated_impact": "medium"
        }
    
    elif change.change_type == "endpoint_added":
        return {
            "severity": "additive",
            "confidence": 0.95,
            "reasoning": "New endpoint added. Fully backward compatible. [Heuristic classification]",
            "recommended_action": "notify_info",
            "migration_path": None,
            "estimated_impact": "low"
        }
    
    elif change.change_type == "endpoint_modified":
        
        # Check for parameter type changes (breaking)
        has_type_change = any(
            pc.change_type == "parameter_type_changed"
            for pc in change.parameter_changes
        )
        
        if has_type_change:
            return {
                "severity": "breaking",
                "confidence": 0.85,
                "reasoning": "Parameter type changed. Likely causes type mismatch errors. [Heuristic classification]",
                "recommended_action": "alert_critical",
                "migration_path": "Update client code to handle new parameter type.",
                "estimated_impact": "high"
            }
        
        # Check for required parameter added (breaking)
        has_required_param_added = any(
            pc.change_type == "parameter_added" and 
            pc.new_value and 
            pc.new_value.get("required", False)
            for pc in change.parameter_changes
        )
        
        if has_required_param_added:
            return {
                "severity": "breaking",
                "confidence": 0.9,
                "reasoning": "Required parameter added. Old clients not sending it will fail validation. [Heuristic classification]",
                "recommended_action": "alert_critical",
                "migration_path": "Update API calls to include new required parameter.",
                "estimated_impact": "high"
            }
        
        # Default for modifications
        return {
            "severity": "additive",
            "confidence": 0.5,
            "reasoning": "Endpoint modified with parameter changes. Review details for impact. [Heuristic classification]",
            "recommended_action": "notify_info",
            "migration_path": None,
            "estimated_impact": "medium"
        }
    
    else:
        # Unknown change type
        return {
            "severity": "minor",
            "confidence": 0.3,
            "reasoning": f"Unknown change type: {change.change_type}. Defaulting to minor. [Heuristic classification]",
            "recommended_action": "ignore",
            "migration_path": None,
            "estimated_impact": "low"
        }
