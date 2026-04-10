"""
Alert formatter for different channels.
Formats alerts as GitHub issues, emails, and Slack messages.
"""

from typing import Dict, Any
from .alert_models import Alert, AlertPriority


# Format alerts for different channels
class AlertFormatter:
    
    # Format alert as GitHub issue
    @staticmethod
    def format_github_issue(alert: Alert) -> Dict[str, Any]:

        # Emoji for severity
        emoji = {
            'breaking': '🔴',
            'deprecation': '⚠️',
            'additive': '✅',
            'minor': 'ℹ️'
        }.get(alert.severity, '📌')
        
        # Title
        title = f"{emoji} {alert.severity.upper()}: {alert.vendor} - {alert.method} {alert.path}"
        
        # Body
        body = f"""## API Change Detected

                    **Vendor**: {alert.vendor}
                    **Endpoint**: `{alert.method} {alert.path}`
                    **Change Type**: {alert.change_type}
                    **Severity**: {alert.severity}
                    **Confidence**: {int(alert.confidence * 100)}%
                    
                    ### Details
                    
                    {alert.reasoning}
                    
                """
        
        # Add migration path if available
        if alert.migration_path:
            body += f"""### Migration Path

                        {alert.migration_path}

                    """
        
        # Add metadata
        body += f"""---

                    **Detected**: {alert.created_at}
                    **Endpoint ID**: `{alert.endpoint_id}`
                """
        
        # Labels
        labels = [
            'api-change',
            alert.severity,
            alert.vendor.lower(),
            f'priority-{alert.priority.value}'
        ]
        
        return {
            'title': title,
            'body': body,
            'labels': labels
        }
    
    # Format alert as email
    @staticmethod
    def format_email(alert: Alert, is_digest: bool = False) -> Dict[str, Any]:

        # Subject
        if not is_digest:
            emoji = {
                'breaking': '🔴',
                'deprecation': '⚠️',
                'additive': '✅',
                'minor': 'ℹ️'
            }.get(alert.severity, '📌')
            
            subject = f"{emoji} {alert.severity.upper()}: {alert.vendor} API Change"
        else:
            subject = "SpecWatch: API Changes Digest"
        
        # HTML body
        severity_color = {
            'breaking': '#dc3545',
            'deprecation': '#ffc107',
            'additive': '#28a745',
            'minor': '#6c757d'
        }.get(alert.severity, '#007bff')
        
        body_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <style>
                                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                                .header {{ background-color: {severity_color}; color: white; padding: 20px; border-radius: 5px; }}
                                .content {{ background-color: #f8f9fa; padding: 20px; margin-top: 20px; border-radius: 5px; }}
                                .badge {{ 
                                    display: inline-block; 
                                    padding: 5px 10px; 
                                    background-color: {severity_color}; 
                                    color: white; 
                                    border-radius: 3px; 
                                    font-weight: bold;
                                }}
                                .endpoint {{ 
                                    font-family: monospace; 
                                    background-color: #e9ecef; 
                                    padding: 10px; 
                                    border-radius: 3px;
                                    margin: 10px 0;
                                }}
                                .footer {{ margin-top: 20px; color: #6c757d; font-size: 12px; }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="header">
                                    <h2>{alert.severity.upper()} API Change Detected</h2>
                                </div>
                                
                                <div class="content">
                                    <p><strong>Vendor:</strong> {alert.vendor}</p>
                                    
                                    <div class="endpoint">
                                        <strong>{alert.method}</strong> {alert.path}
                                    </div>
                                    
                                    <p><span class="badge">{alert.severity}</span> 
                                       <strong>Confidence:</strong> {int(alert.confidence * 100)}%</p>
                                    
                                    <h3>What Changed</h3>
                                    <p>{alert.reasoning}</p>
                                    
                                    {'<h3>Migration Path</h3><p>' + alert.migration_path + '</p>' if alert.migration_path else ''}
                                    
                                    <p class="footer">
                                        Detected: {alert.created_at}<br>
                                        Change Type: {alert.change_type}
                                    </p>
                                </div>
                            </div>
                        </body>
                        </html>
                    """
        
        # Plain text body
        body_text = f"""
                        {alert.severity.upper()} API Change Detected
                        
                        Vendor: {alert.vendor}
                        Endpoint: {alert.method} {alert.path}
                        Severity: {alert.severity}
                        Confidence: {int(alert.confidence * 100)}%
                        
                        DETAILS
                        -------
                        {alert.reasoning}
                        
                        {'MIGRATION PATH' if alert.migration_path else ''}
                        {'---------------' if alert.migration_path else ''}
                        {alert.migration_path or ''}
                        
                        Detected: {alert.created_at}
                        Change Type: {alert.change_type}
                    """
        
        return {
            'subject': subject,
            'body_html': body_html,
            'body_text': body_text.strip()
        }
    
    # Format alert as Slack messages
    @staticmethod
    def format_slack_message(alert: Alert) -> Dict[str, Any]:

        # Color based on severity
        color = {
            'breaking': 'danger',
            'deprecation': 'warning',
            'additive': 'good',
            'minor': '#6c757d'
        }.get(alert.severity, '#007bff')
        
        # Emoji
        emoji = {
            'breaking': ':red_circle:',
            'deprecation': ':warning:',
            'additive': ':white_check_mark:',
            'minor': ':information_source:'
        }.get(alert.severity, ':pushpin:')
        
        # Build Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {alert.severity.upper()}: {alert.vendor} API Change"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Endpoint:*\n`{alert.method} {alert.path}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert.severity}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{int(alert.confidence * 100)}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Change Type:*\n{alert.change_type}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{alert.reasoning}"
                }
            }
        ]
        
        # Add migration path if available
        if alert.migration_path:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Migration Path:*\n{alert.migration_path}"
                }
            })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Add context
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Detected: {alert.created_at} | Endpoint ID: `{alert.endpoint_id}`"
                }
            ]
        })
        
        return {
            'text': f"{emoji} {alert.severity.upper()}: {alert.vendor} - {alert.method} {alert.path}",
            'blocks': blocks,
            'attachments': [
                {
                    'color': color,
                    'fallback': f"{alert.severity.upper()}: {alert.vendor} API change detected"
                }
            ]
        }
