"""
Email alerter.

Sends email alerts via SMTP (Gmail).
Location: specwatch/alerting/email_alerter.py
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from .alert_models import Alert, AlertResult, AlertChannel
from .alert_formatter import AlertFormatter
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)


# Email alerter via SMTP
class EmailAlerter:
    
    # Initialize email alerter
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str]
    ):

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails if isinstance(to_emails, list) else [to_emails]
        self.formatter = AlertFormatter()
        
        logger.info(f"Email alerter initialized: {from_email} -> {', '.join(self.to_emails)}")
    
    # Send email alert
    def send_alert(self, alert: Alert) -> AlertResult:

        try:
            # Format email
            email_data = self.formatter.format_email(alert)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_data['subject']
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add plain text and HTML parts
            part_text = MIMEText(email_data['body_text'], 'plain')
            part_html = MIMEText(email_data['body_html'], 'html')
            
            msg.attach(part_text)
            msg.attach(part_html)
            
            logger.info(f"Sending email alert for {alert.vendor} - {alert.endpoint_id}")
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {', '.join(self.to_emails)}")
            
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=True,
                message=f"Email sent to {len(self.to_emails)} recipient(s)",
                metadata={
                    'recipients': self.to_emails,
                    'subject': email_data['subject']
                }
            )
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=False,
                message="SMTP authentication failed. Check username/password."
            )
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=False,
                message=f"SMTP error: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    # Send digest email with multiple alerts
    def send_digest(self, alerts: List[Alert]) -> AlertResult:

        if not alerts:
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=True,
                message="No alerts to send"
            )
        
        try:
            # Create digest email
            subject = f"SpecWatch: {len(alerts)} API Change(s) Detected"
            
            # Count by severity
            severity_counts = {}
            for alert in alerts:
                severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            
            # Build HTML body
            body_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <style>
                                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                                    .header {{ background-color: #007bff; color: white; padding: 20px; border-radius: 5px; }}
                                    .summary {{ background-color: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                                    .alert-item {{ 
                                        background-color: white; 
                                        border-left: 4px solid #007bff; 
                                        padding: 15px; 
                                        margin: 10px 0; 
                                        border-radius: 3px;
                                    }}
                                    .alert-item.breaking {{ border-left-color: #dc3545; }}
                                    .alert-item.deprecation {{ border-left-color: #ffc107; }}
                                    .alert-item.additive {{ border-left-color: #28a745; }}
                                    .badge {{ 
                                        display: inline-block; 
                                        padding: 3px 8px; 
                                        border-radius: 3px; 
                                        font-size: 12px;
                                        font-weight: bold;
                                    }}
                                    .badge.breaking {{ background-color: #dc3545; color: white; }}
                                    .badge.deprecation {{ background-color: #ffc107; color: black; }}
                                    .badge.additive {{ background-color: #28a745; color: white; }}
                                </style>
                            </head>
                            <body>
                                <div class="container">
                                    <div class="header">
                                        <h2>API Changes Digest</h2>
                                        <p>{len(alerts)} change(s) detected</p>
                                    </div>
                                    
                                    <div class="summary">
                                        <strong>Summary:</strong><br>
                                        {'🔴 Breaking: ' + str(severity_counts.get('breaking', 0)) + '<br>' if severity_counts.get('breaking') else ''}
                                        {'⚠️ Deprecations: ' + str(severity_counts.get('deprecation', 0)) + '<br>' if severity_counts.get('deprecation') else ''}
                                        {'✅ Additive: ' + str(severity_counts.get('additive', 0)) + '<br>' if severity_counts.get('additive') else ''}
                                    </div>
                        """
            
            # Add each alert
            for alert in alerts:
                body_html += f"""
                                    <div class="alert-item {alert.severity}">
                                        <h3>{alert.vendor} - {alert.method} {alert.path}</h3>
                                        <p><span class="badge {alert.severity}">{alert.severity}</span> 
                                           Confidence: {int(alert.confidence * 100)}%</p>
                                        <p>{alert.reasoning}</p>
                                    </div>
                            """
            
            body_html += """
                                </div>
                            </body>
                            </html>
                        """
            
            # Plain text body
            body_text = f"""
                            API Changes Digest
                            ==================
                            
                            {len(alerts)} change(s) detected:
                        """
            
            for alert in alerts:
                body_text += f"""
                                - {alert.severity.upper()}: {alert.vendor} - {alert.method} {alert.path}
                                  {alert.reasoning}
                            """
            
            # Create and send message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            part_text = MIMEText(body_text.strip(), 'plain')
            part_html = MIMEText(body_html, 'html')
            
            msg.attach(part_text)
            msg.attach(part_html)
            
            logger.info(f"Sending digest email with {len(alerts)} alerts")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info("Digest email sent successfully")
            
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=True,
                message=f"Digest email sent with {len(alerts)} alerts",
                metadata={
                    'recipients': self.to_emails,
                    'alert_count': len(alerts)
                }
            )
        
        except Exception as e:
            logger.error(f"Error sending digest email: {str(e)}")
            return AlertResult(
                channel=AlertChannel.EMAIL,
                success=False,
                message=f"Error: {str(e)}"
            )
