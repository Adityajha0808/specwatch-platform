"""
Alerting system for SpecWatch.
Sends notifications via GitHub, Email, and optionally Slack.
"""

from .alert_models import Alert, AlertChannel, AlertPriority, AlertResult
from .alert_formatter import AlertFormatter
from .github_alerter import GitHubAlerter
from .email_alerter import EmailAlerter
from .slack_alerter import SlackAlerter

__all__ = [
    'Alert',
    'AlertChannel',
    'AlertPriority',
    'AlertResult',
    'AlertFormatter',
    'GitHubAlerter',
    'EmailAlerter',
    'SlackAlerter'
]
