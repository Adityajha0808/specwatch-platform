"""
LLM-based classifier for API changes.
Classifies changes by severity and impact.
Adds Redis caching to avoid repeated LLM calls for identical diffs.
"""

import json
import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from dotenv import load_dotenv

from groq import Groq
from specwatch.utils.logger import get_logger
from specwatch.diff.diff_models import EndpointChange, APIDiff
from specwatch.cache.cache_manager import CacheManager
from specwatch.cache.cache_metrics import get_cache_metrics

from .classification_models import (
    ChangeClassification,
    ClassifiedEndpointChange,
    ClassifiedAPIDiff,
    ClassificationSummary
)
from .prompts import build_classification_prompt, build_fallback_classification


load_dotenv()
logger = get_logger(__name__)


# LLM-based classifier for API changes
class ChangeClassifier:
    
    # Initialize classifier with Groq API key
    def __init__(self, api_key: Optional[str] = None):
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Set it in .env file or pass to constructor."
            )
        
        self.client = Groq(api_key=self.api_key)
        self.model = "openai/gpt-oss-120b"

        # Cache support
        self.cache = CacheManager()
        self.metrics = get_cache_metrics()
    
    # Classify a single API change using LLM
    def classify_change(
        self,
        change: EndpointChange,
        full_diff: APIDiff
    ) -> ChangeClassification:

        logger.info(f"Classifying change: {change.change_type} - {change.endpoint_id}")
        
        try:
            # Build prompt
            prompt = build_classification_prompt(change, full_diff)
            
            # Call Groq API
            response = self._call_groq_api(prompt)
            
            # Parse response
            classification_dict = self._parse_response(response)
            
            # Validate and return
            classification = ChangeClassification(**classification_dict)
            
            logger.info(
                f"Classification complete: severity={classification.severity}, "
                f"confidence={classification.confidence:.2f}"
            )
            
            return classification
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}. Using fallback heuristics.")
            
            # Fallback to heuristic classification
            fallback_dict = build_fallback_classification(change)
            return ChangeClassification(**fallback_dict)
    
    # Call Groq API
    def _call_groq_api(self, prompt: str) -> str:

        logger.debug("Calling Groq API...")
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an API versioning expert. "
                        "You analyze API changes and classify them by severity. "
                        "You always respond with valid JSON only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Low temperature for consistent, deterministic output
            max_completion_tokens=1024,  # Sufficient for classification JSON
            top_p=0.9,  # Slightly focused sampling
            reasoning_effort="medium",
            stream=False,  # Disable streaming for easier JSON parsing
            stop=None
        )
        
        response_text = completion.choices[0].message.content
        
        logger.debug(f"Groq API response received: {len(response_text)} chars")
        
        return response_text
    
    # Parse LLM response into classification dict
    def _parse_response(self, response_text: str) -> Dict[str, Any]:

        # Clean response (remove markdown code fences if present)
        cleaned = response_text.strip()
        
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # Remove ```json
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]  # Remove ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # Remove trailing ```
        
        cleaned = cleaned.strip()
        
        # Parse JSON
        try:
            result = json.loads(cleaned)
            logger.debug("Successfully parsed classification JSON")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {cleaned[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    # Deterministic cache key for whole diff
    def _compute_diff_hash(self, diff: APIDiff) -> str:

        diff_json = json.dumps(
            diff.model_dump(),
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(diff_json.encode()).hexdigest()[:16]
    
    # Classify all changes in a diff with caching
    def classify_diff(self, diff: APIDiff) -> ClassifiedAPIDiff:


        logger.info(
            f"Classifying diff for {diff.vendor}: "
            f"{len(diff.endpoint_changes)} changes"
        )

        # Cache lookup
        diff_hash = self._compute_diff_hash(diff)

        cached = self.cache.get_classification(diff_hash)
        if cached:
            self.metrics.record_classification_hit()
            logger.info(f"✓ Classification cache HIT for {diff.vendor}")
            return ClassifiedAPIDiff(**json.loads(cached))

        self.metrics.record_classification_miss()
        logger.info(
            f"✗ Classification cache MISS for {diff.vendor}, calling LLM..."
        )
        
        classified_changes = []
        
        # Classify each change
        for idx, change in enumerate(diff.endpoint_changes):
            logger.info(f"Processing change {idx + 1}/{len(diff.endpoint_changes)}")
            
            try:
                classification = self.classify_change(change, diff)
                
                classified_changes.append(ClassifiedEndpointChange(
                    change_type=change.change_type,
                    endpoint_id=change.endpoint_id,
                    path=change.path,
                    method=change.method,
                    classification=classification,
                    details=change.model_dump()
                ))
                
            except Exception as e:
                logger.error(f"Failed to classify change {change.endpoint_id}: {e}")
                # Skip this change rather than failing entire classification
                continue
        
        # Build summary
        summary = self._build_summary(classified_changes)
        
        # Create classified diff
        classified_diff = ClassifiedAPIDiff(
            vendor=diff.vendor,
            baseline_version=diff.baseline_version,
            latest_version=diff.latest_version,
            classified_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S') + "Z",
            diff_summary=diff.summary.model_dump(),
            classified_changes=classified_changes,
            classification_summary=summary,
            has_breaking_changes=summary.breaking_changes > 0,
            has_deprecations=summary.deprecations > 0,
            requires_immediate_action=summary.critical_alerts_needed > 0
        )

        # Cache final result for 30 days
        self.cache.set_classification(
            diff_hash,
            json.dumps(classified_diff.model_dump(), default=str),
            ttl=2592000
        )
        
        logger.info(
            f"Classification complete for {diff.vendor}: "
            f"breaking={summary.breaking_changes}, "
            f"deprecations={summary.deprecations}, "
            f"additive={summary.additive_changes}"
        )
        
        return classified_diff
    
    # Build classification summary from classified changes
    def _build_summary(
        self,
        classified_changes: list
    ) -> ClassificationSummary:
        """Build classification summary from classified changes."""
        
        summary = ClassificationSummary(total_changes=len(classified_changes))
        
        for change in classified_changes:
            # Count by severity

            severity = change.classification.severity
            action = change.classification.recommended_action

            if severity == "breaking":
                summary.breaking_changes += 1
            elif severity == "deprecation":
                summary.deprecations += 1
            elif severity == "additive":
                summary.additive_changes += 1
            elif severity == "minor":
                summary.minor_changes += 1
            
            # Count by action
            if action == "alert_critical":
                summary.critical_alerts_needed += 1
            elif action == "alert_warning":
                summary.warning_alerts_needed += 1
            elif action == "notify_info":
                summary.info_notifications += 1
        
        return summary