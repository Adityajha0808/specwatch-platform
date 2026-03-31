"""
Alert management routes.
Handles alert preview and manual sending.
"""

from flask import Blueprint, request, jsonify, current_app
from app.utils.data_loader import DataLoader
from specwatch.alerting import (
    Alert,
    AlertFormatter,
    GitHubAlerter,
    EmailAlerter,
    SlackAlerter
)
import json
from pathlib import Path

bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')


# Preview what alert would look like
@bp.route('/preview/<vendor>/<int:change_index>')
def preview_alert(vendor, change_index):

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    
    # Get recent changes for vendor
    changes = loader.get_recent_changes(limit=100, vendor=vendor)
    
    if change_index >= len(changes):
        return jsonify({"error": "Change not found"}), 404
    
    change_data = changes[change_index]
    
    # Create Alert object (but don't send)
    alert_dict = {
        'endpoint_id': change_data['endpoint_id'],
        'path': change_data['path'],
        'method': change_data['method'],
        'change_type': change_data['change_type'],
        'classification': {
            'severity': change_data['severity'],
            'confidence': change_data['confidence'],
            'reasoning': change_data['reasoning'],
            'recommended_action': change_data['recommended_action'],
            'migration_path': change_data.get('migration_path'),
            'estimated_impact': change_data['impact']
        }
    }
    
    alert = Alert.from_classified_change(vendor, alert_dict)
    
    # Format for each channel
    formatter = AlertFormatter()
    
    preview = {
        "github": formatter.format_github_issue(alert),
        "email": formatter.format_email(alert),
    }
    
    if current_app.config['SLACK_ENABLED']:
        preview["slack"] = formatter.format_slack_message(alert)
    
    return jsonify(preview)


# Manually send alert
@bp.route('/send', methods=['POST'])
def send_alert():

    data = request.json
    vendor = data.get('vendor')
    change_index = data.get('change_index')
    channels = data.get('channels', [])
    
    if not vendor or change_index is None:
        return jsonify({"error": "vendor and change_index required"}), 400
    
    # Load change data
    loader = DataLoader(current_app.config['STORAGE_DIR'])
    changes = loader.get_recent_changes(limit=100, vendor=vendor)
    
    if change_index >= len(changes):
        return jsonify({"error": "Change not found"}), 404
    
    change_data = changes[change_index]
    
    # Create Alert
    alert_dict = {
        'endpoint_id': change_data['endpoint_id'],
        'path': change_data['path'],
        'method': change_data['method'],
        'change_type': change_data['change_type'],
        'classification': {
            'severity': change_data['severity'],
            'confidence': change_data['confidence'],
            'reasoning': change_data['reasoning'],
            'recommended_action': change_data['recommended_action'],
            'migration_path': change_data.get('migration_path'),
            'estimated_impact': change_data['impact']
        }
    }
    
    alert = Alert.from_classified_change(vendor, alert_dict)
    
    results = {}
    
    # GitHub
    if 'github' in channels and current_app.config['GITHUB_ENABLED']:
        try:
            github_alerter = GitHubAlerter(
                token=current_app.config['GITHUB_TOKEN'],
                repo=current_app.config['GITHUB_REPO']
            )
            result = github_alerter.send_alert(alert)
            results['github'] = result.dict()
        except Exception as e:
            results['github'] = {"success": False, "message": str(e)}
    
    # Email
    if 'email' in channels and current_app.config['EMAIL_ENABLED']:
        try:
            email_alerter = EmailAlerter(
                smtp_host=current_app.config['SMTP_HOST'],
                smtp_port=current_app.config['SMTP_PORT'],
                username=current_app.config['SMTP_USERNAME'],
                password=current_app.config['SMTP_PASSWORD'],
                from_email=current_app.config['EMAIL_FROM'],
                to_emails=[current_app.config['EMAIL_TO']]
            )
            result = email_alerter.send_alert(alert)
            results['email'] = result.dict()
        except Exception as e:
            results['email'] = {"success": False, "message": str(e)}
    
    # Slack
    if 'slack' in channels and current_app.config['SLACK_ENABLED']:
        try:
            slack_alerter = SlackAlerter(
                bot_token=current_app.config['SLACK_BOT_TOKEN'],
                channel=current_app.config['SLACK_CHANNEL']
            )
            result = slack_alerter.send_alert(alert)
            results['slack'] = result.dict()
        except Exception as e:
            results['slack'] = {"success": False, "message": str(e)}
    
    return jsonify({
        "success": True,
        "results": results
    })


# Get alert history
@bp.route('/history')
def alert_history():

    storage_dir = Path(current_app.config['STORAGE_DIR'])
    alerts_dir = storage_dir / "alerts"
    
    if not alerts_dir.exists():
        return jsonify({"vendors": {}})
    
    history = {}
    
    # Load history for each vendor
    for history_file in alerts_dir.glob("*_alert_history.json"):
        vendor = history_file.stem.replace('_alert_history', '')
        
        with open(history_file, 'r') as f:
            history[vendor] = json.load(f)
    
    return jsonify({"vendors": history})


# Get or update alert settings
@bp.route('/settings', methods=['GET', 'PUT'])
def alert_settings():

    if request.method == 'GET':
        return jsonify({
            "github_enabled": current_app.config['GITHUB_ENABLED'],
            "github_configured": bool(current_app.config.get('GITHUB_TOKEN')),
            "email_enabled": current_app.config['EMAIL_ENABLED'],
            "email_configured": bool(current_app.config.get('SMTP_USERNAME')),
            "slack_enabled": current_app.config['SLACK_ENABLED'],
            "slack_configured": bool(current_app.config.get('SLACK_BOT_TOKEN'))
        })
    
    # PUT: Update settings (save to .env or database)
    # For now, just return current settings
    return jsonify({"success": True})
