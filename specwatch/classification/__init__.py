"""
Classification module for API change severity analysis.
Provides LLM-based classification of API changes.
"""

from .classifier import ChangeClassifier
from .classification_models import (
    ChangeClassification,
    ClassifiedEndpointChange,
    ClassifiedAPIDiff,
    ClassificationSummary
)

__all__ = [
    "ChangeClassifier",
    "ChangeClassification",
    "ClassifiedEndpointChange",
    "ClassifiedAPIDiff",
    "ClassificationSummary"
]
