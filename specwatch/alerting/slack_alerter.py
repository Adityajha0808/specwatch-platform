#!/usr/bin/env python3
"""
Slack alerter for SpecWatch.
Sends formatted alerts to Slack channel via webhook.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime

from specwatch.alerting.alert_models import Alert
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Sends alerts to Slack via webhook
class SlackAlerter:
    
    # Initialize Slack alerter
    def __init__(self):

        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            logger.warning("Slack webhook URL not configured, Slack alerts disabled")
        else:
            logger.info("Slack alerter initialized")
    
    # Send single alert to Slack
    def send_alert(self, alert: Alert) -> bool:

        if not self.enabled:
            logger.debug("Slack disabled, skipping alert")
            return False
        
        try:
            # Build Slack message
            message = self._build_message(alert)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✓ Slack alert sent for {alert.vendor}: {alert.title}")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return False
        
        except requests.exceptions.Timeout:
            logger.error("Slack webhook timeout")
            return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    # Send multiple alerts in a single message
    def send_batch_alert(self, alerts: List[Alert]) -> bool:

        if not self.enabled:
            logger.debug("Slack disabled, skipping batch alert")
            return False
        
        if not alerts:
            logger.debug("No alerts to send")
            return True
        
        try:
            # Group by vendor
            by_vendor = {}
            for alert in alerts:
                vendor = alert.vendor
                if vendor not in by_vendor:
                    by_vendor[vendor] = []
                by_vendor[vendor].append(alert)
            
            # Build summary message
            message = self._build_summary_message(by_vendor)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✓ Slack batch alert sent ({len(alerts)} alerts)")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack batch alert: {e}")
            return False
    
    # Build Slack message payload
    def _build_message(self, alert: Alert) -> Dict:

        # Color based on severity
        color = self._get_color(alert.severity)
        
        # Emoji based on severity
        emoji = self._get_emoji(alert.severity)
        
        # GitHub issue link (if available)
        github_link = ""
        if alert.metadata and alert.metadata.get('github_issue_url'):
            github_link = f"\n🔗 <{alert.metadata['github_issue_url']}|View GitHub Issue>"
        
        # Build message
        message = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} {alert.vendor.upper()} API Change Detected",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:*\n{alert.severity.upper()}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Category:*\n{alert.category}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{alert.title}*\n{alert.description}"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Add GitHub link if available
        if github_link:
            message["attachments"][0]["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": github_link
                }
            })
        
        # Add footer
        message["attachments"][0]["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"SpecWatch Alert • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                }
            ]
        })
        
        return message
    
    # Build summary message for multiple alerts
    def _build_summary_message(self, by_vendor: Dict[str, List[Alert]]) -> Dict:

        total_alerts = sum(len(alerts) for alerts in by_vendor.values())
        
        # Count by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for alerts in by_vendor.values():
            for alert in alerts:
                severity = alert.severity.lower()
                if severity in severity_counts:
                    severity_counts[severity] += 1
        
        # Build summary text
        summary_lines = []
        for vendor, alerts in by_vendor.items():
            summary_lines.append(f"• *{vendor.upper()}*: {len(alerts)} change(s)")
        
        summary_text = "\n".join(summary_lines)
        
        # Build message
        message = {
            "text": f"📊 API Changes Detected ({total_alerts} total)",
            "attachments": [
                {
                    "color": "#36a64f" if severity_counts["critical"] == 0 else "#ff0000",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"📊 API Changes Summary",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Total Changes:*\n{total_alerts}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Vendors:*\n{len(by_vendor)}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Severity Breakdown:*\n🔴 Critical: {severity_counts['critical']}\n🟠 High: {severity_counts['high']}\n🟡 Medium: {severity_counts['medium']}\n🟢 Low: {severity_counts['low']}"
                            }
                        },
                        {
                            "type": "divider"
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Affected Vendors:*\n{summary_text}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"SpecWatch Alert • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        return message
    
    # Get color for severity
    def _get_color(self, severity: str) -> str:

        colors = {
            "critical": "#ff0000",  # Red
            "high": "#ff6600",      # Orange
            "medium": "#ffcc00",    # Yellow
            "low": "#36a64f"        # Green
        }
        return colors.get(severity.lower(), "#808080")  # Gray default
    
    # Get emoji for severity
    def _get_emoji(self, severity: str) -> str:

        emojis = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️"
        }
        return emojis.get(severity.lower(), "📢")


# Convenience function to send single Slack alert
def send_slack_alert(alert: Alert) -> bool:

    alerter = SlackAlerter()
    return alerter.send_alert(alert)

# Convenience function to send batch Slack alert
def send_slack_batch_alert(alerts: List[Alert]) -> bool:

    alerter = SlackAlerter()
    return alerter.send_batch_alert(alerts)
