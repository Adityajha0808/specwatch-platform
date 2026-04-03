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
from specwatch.alerting.alert_models import Alert, AlertChannel, AlertPriority
from specwatch.utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


# Alerting pipeline orchestrator. Sends alerts via configured channels.
class AlertingPipeline:
    
    # Initialize alerting pipeline
    def __init__(self, test_mode: bool = False):

        self.test_mode = test_mode
        self.github_alerter: Optional[GitHubAlerter] = None
        self.email_alerter: Optional[EmailAlerter] = None
        
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
    
    # Run alerting pipeline
    def run(self) -> Dict[str, int]:

        if not self.input_path.exists():
            logger.warning(f"Input path does not exist: {self.input_path}")
            return {"total": 0, "sent": 0, "failed": 0}
        
        # Discover vendors
        vendors = self._discover_vendors()
        
        if not vendors:
            logger.info("No vendors found with classified diffs")
            return {"total": 0, "sent": 0, "failed": 0}
        
        logger.info(f"Processing alerts for {len(vendors)} vendors")
        
        total_alerts = 0
        sent_alerts = 0
        failed_alerts = 0
        
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
                
                # Send via configured channels
                success = self._send_alert(alert)
                
                if success:
                    sent_alerts += 1
                else:
                    failed_alerts += 1
        
        logger.info(f"Alerting complete: {sent_alerts}/{total_alerts} alert(s) sent successfully")
        
        return {
            "total": total_alerts,
            "sent": sent_alerts,
            "failed": failed_alerts
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
            channels=["github", "email"],
            detected_at=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
        )
        
        return alert
    
    # Send alert via configured channels
    def _send_alert(self, alert: Alert) -> bool:

        success = False
        
        # Determine channels based on severity
        channels = self._determine_channels(alert.severity)
        
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
    
    # Determine which channels to use based on severity
    def _determine_channels(self, severity: str) -> List[AlertChannel]:

        if severity == "breaking":
            # Breaking: GitHub issue + Email
            return [AlertChannel.GITHUB, AlertChannel.EMAIL]
        
        elif severity == "deprecation":
            # Deprecation: GitHub issue only
            return [AlertChannel.GITHUB]
        
        elif severity == "additive":
            # Additive: Email only (informational)
            return [AlertChannel.EMAIL]
        
        else:
            # Minor: No alerts (logged only)
            return []


# Main entry point for alerting pipeline
# Usage:
#   python3 -m pipelines.alerting_pipeline              # Production mode
#   python3 -m pipelines.alerting_pipeline --test       # Test mode
def main():

    parser = argparse.ArgumentParser(description="SpecWatch Alerting Pipeline")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (use test fixtures instead of production data)"
    )
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = AlertingPipeline(test_mode=args.test)
    results = pipeline.run()
    
    # Log summary
    logger.info(f"Alerting pipeline complete: {results['sent']}/{results['total']} successful")
    
    # Exit with error code if any failed
    if results['failed'] > 0:
        logger.warning(f"{results['failed']} alerts failed to send")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
