#!/usr/bin/env python3
"""
Alerting pipeline.
Orchestrates sending alerts for classified API changes.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, UTC

from specwatch.alerting.github_alerter import GitHubAlerter
from specwatch.alerting.email_alerter import EmailAlerter
from specwatch.alerting.slack_alerter import SlackAlerter
from specwatch.alerting.alert_models import Alert, AlertChannel, AlertPriority
from specwatch.utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


# Alerting pipeline orchestrator. Sends alerts via configured channels.
class AlertingPipeline:
    
    # Initialize alerting pipeline
    def __init__(self, vendors_input: Optional[List[str]] = None, test_mode: bool = False, batch_slack: bool = True):

        self.vendors_input = vendors_input
        self.test_mode = test_mode
        self.batch_slack = batch_slack
        self.github_alerter: Optional[GitHubAlerter] = None
        self.email_alerter: Optional[EmailAlerter] = None
        self.slack_alerter: Optional[SlackAlerter] = None
        
        # Set input path based on mode
        if test_mode:
            self.input_path = Path("test/classified_output")
            logger.info("Alerting pipeline started (TEST MODE)")
        else:
            self.input_path = Path("storage/classified_diffs")
            logger.info("Alerting pipeline started (PRODUCTION MODE)")
        
        # Initialize alerters
        self._init_alerters()
    
    # Initialize alert channels based on environment variables
    def _init_alerters(self):

        # GitHub alerter
        try:
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo = os.getenv("GITHUB_REPO")
            github_enabled = os.getenv("GITHUB_ENABLED", "false").lower() == "true"
            
            if github_enabled and github_token and github_repo:
                self.github_alerter = GitHubAlerter(github_token, github_repo)
                logger.info("GitHub alerter enabled")
            else:
                logger.info("GitHub alerter disabled (not configured)")
        except Exception as e:
            logger.warning(f"Failed to initialize GitHub alerter: {e}")
        
        # Email alerter
        try:
            email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = os.getenv("SMTP_PORT")
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            email_from = os.getenv("EMAIL_FROM")
            email_to = os.getenv("EMAIL_TO")
            
            if email_enabled and smtp_host and smtp_port and smtp_username and smtp_password and email_from and email_to:
                self.email_alerter = EmailAlerter(smtp_host, smtp_port, smtp_username, smtp_password, email_from, email_to)
                logger.info("Email alerter enabled")
            else:
                logger.info("Email alerter disabled (not configured)")
        except Exception as e:
            logger.warning(f"Failed to initialize email alerter: {e}")
        
        # Slack alerter
        try:
            slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            
            if slack_webhook_url:
                self.slack_alerter = SlackAlerter()
                logger.info("✓ Slack alerter enabled")
                if self.batch_slack:
                    logger.info("  Mode: Batch summary (one message)")
                else:
                    logger.info("  Mode: Individual messages")
            else:
                logger.info("Slack alerter disabled (SLACK_WEBHOOK_URL not configured)")
        except Exception as e:
            logger.warning(f"Failed to initialize Slack alerter: {e}")
    
    # Run alerting pipeline
    def run(self) -> Dict[str, int]:

        if not self.input_path.exists():
            logger.warning(f"Input path does not exist: {self.input_path}")
            return {"total": 0, "sent": 0, "failed": 0, "slack_sent": 0}
        
        # Discover vendors
        vendors = self._discover_vendors()
        
        if not vendors:
            logger.info("No vendors found with classified diffs")
            return {"total": 0, "sent": 0, "failed": 0, "slack_sent": 0}
        
        # Filter vendors if specified
        if self.vendors_input:
            vendors = [v for v in vendors if v in self.vendors_input]
            logger.info(f"Filtered to {len(vendors)} requested vendors: {vendors}")
        
        logger.info(f"Processing alerts for {len(vendors)} vendors")
        
        total_alerts = 0
        sent_alerts = 0
        failed_alerts = 0
        all_alerts_for_slack = []  # Collect for batch Slack alert
        
        # Process each vendor
        for vendor in vendors:
            logger.info(f"Processing alerts for {vendor}")
            
            # Load classified diff
            classified_diff = self._load_classified_diff(vendor)
            
            if not classified_diff:
                logger.warning(f"No classified diff found for {vendor}")
                continue
            
            # Extract critical changes (breaking + deprecations)
            critical_changes = self._extract_critical_changes(classified_diff)
            
            if not critical_changes:
                logger.info(f"No critical changes for {vendor}, skipping alerts")
                continue
            
            logger.info(f"Found {len(critical_changes)} critical changes for {vendor}")
            
            # Send alerts for each critical change
            for change in critical_changes:
                total_alerts += 1
                
                # Create alert object
                alert = self._create_alert(vendor, change, classified_diff)
                
                # Send via GitHub and Email
                success = self._send_alert_traditional_channels(alert)
                
                if success:
                    sent_alerts += 1
                else:
                    failed_alerts += 1
                
                # Collect for Slack (batch or individual)
                if self.slack_alerter:
                    if self.batch_slack:
                        # Collect for batch summary
                        all_alerts_for_slack.append(alert)
                    else:
                        # Send individual Slack message
                        slack_success = self._send_slack_alert_individual(alert)
                        if slack_success:
                            logger.info(f"✓ Slack alert sent for {vendor}")
        
        
        # Send batch Slack alert if enabled
        slack_batch_sent = 0
        if self.batch_slack and all_alerts_for_slack and self.slack_alerter:
            slack_success = self._send_slack_batch(all_alerts_for_slack)
            if slack_success:
                slack_batch_sent = 1
                logger.info(f"✓ Batch Slack alert sent ({len(all_alerts_for_slack)} alerts)")
            else:
                logger.warning("Batch Slack alert failed")
        
        # Summary
        logger.info("="*60)
        logger.info(f"Alerting pipeline completed:")
        logger.info(f"  - Total alerts: {total_alerts}")
        logger.info(f"  - GitHub/Email sent: {sent_alerts}")
        logger.info(f"  - GitHub/Email failed: {failed_alerts}")
        if self.slack_alerter:
            if self.batch_slack:
                logger.info(f"  - Slack batch sent: {slack_batch_sent}")
            else:
                logger.info(f"  - Slack individual: {len(all_alerts_for_slack)}")
        logger.info("="*60)
        
        return {
            "total": total_alerts,
            "sent": sent_alerts,
            "failed": failed_alerts,
            "slack_sent": slack_batch_sent if self.batch_slack else len(all_alerts_for_slack)
        }
    
    # Discover vendors with classified diffs
    def _discover_vendors(self) -> List[str]:

        vendors = []
        
        if not self.input_path.exists():
            return vendors
        
        for vendor_dir in self.input_path.iterdir():
            if vendor_dir.is_dir():
                vendors.append(vendor_dir.name)
        
        return sorted(vendors)
    
    # Load latest classified diff for vendor
    def _load_classified_diff(self, vendor: str) -> Optional[Dict]:

        vendor_path = self.input_path / vendor
        
        if not vendor_path.exists():
            return None
        
        # Find latest classified diff
        diff_files = sorted(vendor_path.glob("classified_diff_*.json"))
        
        if not diff_files:
            return None
        
        latest_file = diff_files[-1]
        
        try:
            with open(latest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load classified diff for {vendor}: {e}")
            return None
    
    # Extract breaking changes and deprecations from classified diff
    def _extract_critical_changes(self, classified_diff: Dict) -> List[Dict]:

        critical_changes = []
        
        # Get all classified changes
        changes = classified_diff.get("classified_changes", [])
        
        for change in changes:
            severity = change.get("severity", "")
            
            # Include breaking changes and deprecations
            if severity in ["breaking", "deprecation"]:
                critical_changes.append(change)
        
        return critical_changes
    
    # Create alert object from change data
    def _create_alert(self, vendor: str, change: Dict, classified_diff: Dict) -> Alert:

        # Determine priority
        severity = change.get("severity", "minor")
        if severity == "breaking":
            priority = AlertPriority.CRITICAL
        elif severity == "deprecation":
            priority = AlertPriority.WARNING
        else:
            priority = AlertPriority.INFO

        # Determine channels (GitHub + Email for now, Slack handled separately)
        channels = []
        if severity == "breaking":
            channels = [AlertChannel.GITHUB, AlertChannel.EMAIL]
        elif severity == "deprecation":
            channels = [AlertChannel.GITHUB]
        else:
            channels = [AlertChannel.EMAIL]
        
        # Build alert
        alert = Alert(
            vendor=vendor,
            title=f"{severity.upper()}: {change.get('method', '')} {change.get('path', '')}",
            severity=severity,
            priority=priority,
            endpoint_id=change.get("endpoint_id", ""),
            method=change.get("method", ""),
            path=change.get('path', ""),
            change_type=change.get("change_type", ""),
            reasoning=change.get("reasoning", ""),
            migration_path=change.get("migration_path"),
            impact=change.get("impact", "unknown"),
            confidence=change.get("confidence", 0.0),
            baseline_version=classified_diff.get("baseline_version", ""),
            latest_version=classified_diff.get("latest_version", ""),
            channels=channels,
            detected_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
        )
        
        return alert
    
    # Send alert via configured traditional channels
    def _send_alert_traditional_channels(self, alert: Alert) -> bool:

        success = False
        
        # Determine channels based on severity
        channels = alert.channels
        
        logger.info(f"Sending alert via channels: {[c.value for c in channels]}")
        
        # Send to GitHub
        if AlertChannel.GITHUB in channels and self.github_alerter:
            try:
                result = self.github_alerter.send_alert(alert)
                if result.success:
                    logger.info(f"GitHub alert sent: {result.message}")
                    success = True
                else:
                    logger.error(f"GitHub alert failed: {result.message}")
            except Exception as e:
                logger.error(f"GitHub alert error: {e}")
        
        # Send to Email
        if AlertChannel.EMAIL in channels and self.email_alerter:
            try:
                result = self.email_alerter.send_alert(alert)
                if result.success:
                    logger.info(f"Email alert sent: {result.message}")
                    success = True
                else:
                    logger.error(f"Email alert failed: {result.message}")
            except Exception as e:
                logger.error(f"Email alert error: {e}")
        
        return success
    
    # Send individual Slack alert
    def _send_slack_alert_individual(self, alert: Alert) -> bool:

        if not self.slack_alerter:
            return False
        
        try:
            success = self.slack_alerter.send_alert(alert)
            return success
        except Exception as e:
            logger.error(f"Slack alert error: {e}")
            return False
    
    # Send batch Slack summary
    def _send_slack_batch(self, alerts: List[Alert]) -> bool:

        if not self.slack_alerter:
            return False
        
        try:
            success = self.slack_alerter.send_batch_alert(alerts)
            return success
        except Exception as e:
            logger.error(f"Slack batch alert error: {e}")
            return False


# To run alerting as part of full pipeline from UI/terminal
def run_alerting(vendors: Optional[List[str]] = None, test_mode: bool = False, batch_slack: bool = True):
    pipeline = AlertingPipeline(
        vendors_input=vendors,
        test_mode=test_mode,
        batch_slack=batch_slack
    )
    return pipeline.run()

# Main entry point for alerting pipeline
# Usage:
#   python3 -m pipelines.alerting_pipeline              # Production mode
#   python3 -m pipelines.alerting_pipeline --test       # Test mode
def main():

    parser = argparse.ArgumentParser(description="SpecWatch Alerting Pipeline")
    parser.add_argument(
        "--vendors",
        nargs="+",
        help="Specific vendors to alert (e.g., stripe). If not specified, alerts for all."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (use test fixtures instead of production data)"
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="Send individual Slack messages (default: batch summary)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()

    # Enable debug logging if requested
    if args.debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # Run pipeline
    pipeline = AlertingPipeline(
        vendors_input=args.vendors,
        test_mode=args.test,
        batch_slack=not args.individual  # Batch by default, individual if flag set
    )
    results = pipeline.run()
    
    # Log summary
    logger.info(f"Alerting pipeline complete: {results['sent']}/{results['total']} GitHub/Email alerts successful")
    if results['slack_sent'] > 0:
        logger.info(f"Slack alerts: {results['slack_sent']} message(s) sent")
    
    # Exit with error code if any failed
    if results['failed'] > 0:
        logger.warning(f"{results['failed']} alerts failed to send")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
