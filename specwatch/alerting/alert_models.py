"""
Alert data models.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, UTC


# Alert delivery channels
class AlertChannel(str, Enum):

    GITHUB = "github"
    EMAIL = "email"
    SLACK = "slack"


# Alert priority levels
class AlertPriority(str, Enum):
    CRITICAL = "critical"    # Breaking changes - immediate action needed
    WARNING = "warning"      # Deprecations - plan migration
    INFO = "info"           # Additive changes - informational


# Alert to be sent; Represents a single alert about an API change
class Alert(BaseModel):

    vendor: str
    endpoint_id: str
    path: str
    method: str
    change_type: str
    severity: str
    confidence: float
    reasoning: str
    migration_path: Optional[str]
    priority: AlertPriority
    channels: List[AlertChannel]
    created_at: str = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')

    title: Optional[str] = None
    impact: Optional[str] = "unknown"
    baseline_version: Optional[str] = ""
    latest_version: Optional[str] = ""
    detected_at: Optional[str] = None
    
    # Create Alert from classified change
    @classmethod
    def from_classified_change(cls, vendor: str, change: dict) -> 'Alert':

        # Determine priority from severity
        severity = change['classification']['severity']
        if severity == 'breaking':
            priority = AlertPriority.CRITICAL
        elif severity == 'deprecation':
            priority = AlertPriority.WARNING
        else:
            priority = AlertPriority.INFO
        
        # Determine channels based on priority
        if priority == AlertPriority.CRITICAL:
            channels = [AlertChannel.GITHUB, AlertChannel.EMAIL]
        elif priority == AlertPriority.WARNING:
            channels = [AlertChannel.GITHUB]
        else:
            channels = [AlertChannel.EMAIL]
        
        return cls(
            vendor=vendor,
            endpoint_id=change['endpoint_id'],
            path=change['path'],
            method=change['method'],
            change_type=change['change_type'],
            severity=severity,
            confidence=change['classification']['confidence'],
            reasoning=change['classification']['reasoning'],
            migration_path=change['classification'].get('migration_path'),
            priority=priority,
            channels=channels
        )


# Result of sending an alert
class AlertResult(BaseModel):

    channel: AlertChannel
    success: bool
    message: str
    metadata: Optional[dict] = None
    sent_at: str = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
