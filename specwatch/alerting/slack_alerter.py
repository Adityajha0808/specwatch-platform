"""
Slack alerter: Sends alerts to Slack channel.
"""

import logging
from typing import Optional
from .alert_models import Alert, AlertResult, AlertChannel
from .alert_formatter import AlertFormatter

logger = logging.getLogger(__name__)


# Sends alerts to Slack channel using Slack SDK
class SlackAlerter:
    
    # Initialize Slack alerter
    def __init__(self, bot_token: str, channel: str):

        self.bot_token = bot_token
        self.channel = channel
        self.formatter = AlertFormatter()
        
        # Try to import Slack SDK (optional dependency)
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            self.client = WebClient(token=bot_token)
            self.SlackApiError = SlackApiError
            
            logger.info(f"Slack alerter initialized for channel: {channel}")
        
        except ImportError:
            logger.warning("slack_sdk not installed. Install with: pip install slack-sdk")
            self.client = None
            self.SlackApiError = Exception
    
    # Send alert to Slack
    def send_alert(self, alert: Alert) -> AlertResult:

        if not self.client:
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=False,
                message="Slack SDK not installed"
            )
        
        try:
            # Format as Slack message
            message_data = self.formatter.format_slack_message(alert)
            
            logger.info(f"Sending Slack alert for {alert.vendor} - {alert.endpoint_id}")
            
            # Send message
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message_data['text'],
                blocks=message_data['blocks'],
                attachments=message_data.get('attachments', [])
            )
            
            logger.info(f"Slack message sent: {response['ts']}")
            
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=True,
                message="Message sent to Slack",
                metadata={
                    'channel': self.channel,
                    'ts': response['ts']
                }
            )
        
        except self.SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=False,
                message=f"Slack API error: {e.response['error']}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=False,
                message=f"Error: {str(e)}"
            )

    # Send alert as reply in existing thread
    def send_thread_reply(self, alert: Alert, thread_ts: str) -> AlertResult:

        if not self.client:
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=False,
                message="Slack SDK not installed"
            )
        
        try:
            message_data = self.formatter.format_slack_message(alert)
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message_data['text'],
                blocks=message_data['blocks'],
                thread_ts=thread_ts
            )
            
            logger.info(f"Slack thread reply sent: {response['ts']}")
            
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=True,
                message="Reply sent to Slack thread",
                metadata={
                    'channel': self.channel,
                    'ts': response['ts'],
                    'thread_ts': thread_ts
                }
            )
        
        except Exception as e:
            logger.error(f"Error sending Slack thread reply: {str(e)}")
            return AlertResult(
                channel=AlertChannel.SLACK,
                success=False,
                message=f"Error: {str(e)}"
            )
