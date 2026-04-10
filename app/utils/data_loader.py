"""
Data loader utility for Flask app.
Loads data from storage directories (classified diffs, normalized snapshots, etc).
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from collections import defaultdict


# Load data from SpecWatch storage
class DataLoader:

    # Initialize data loader    
    def __init__(self, storage_dir: Path):

        self.storage_dir = Path(storage_dir)
        self.config_dir = Path("specwatch/config/json")

    # Get list of all configured vendors
    def get_all_vendors(self) -> List[Dict[str, Any]]:

        # Load from vendors.json
        vendors_file = self.config_dir / "vendors.json"
        
        if not vendors_file.exists():
            return []
        
        with open(vendors_file, 'r') as f:
            config = json.load(f)
        
        vendors = []
        for vendor_config in config.get("vendors", []):
            vendor_name = vendor_config["name"]
            
            # Get additional details
            status = self._get_vendor_status(vendor_name)
            
            vendors.append({
                "name": vendor_name,
                "display_name": vendor_config.get("display_name", vendor_name.capitalize()),
                "status": status["status"],
                "last_sync": status["last_sync"],
                "changes_count": status["changes_count"],
                "breaking_count": status["breaking_count"],
                "urls": self._get_vendor_urls(vendor_name)
            })
        
        return vendors
    
    # Get current status for a vendor
    def _get_vendor_status(self, vendor: str) -> Dict[str, Any]:

        # Check latest classified diff
        classified_dir = self.storage_dir / "classified_diffs" / vendor
        
        if not classified_dir.exists():
            return {
                "status": "unknown",
                "last_sync": None,
                "changes_count": 0,
                "breaking_count": 0
            }
        
        # Find latest classified diff
        classified_files = sorted(classified_dir.glob("classified_diff_*.json"), reverse=True)
        
        if not classified_files:
            return {
                "status": "no_data",
                "last_sync": None,
                "changes_count": 0,
                "breaking_count": 0
            }
        
        # Load latest
        with open(classified_files[0], 'r') as f:
            classified_diff = json.load(f)
        
        # Determine status
        breaking = classified_diff.get("classification_summary", {}).get("breaking_changes", 0)
        deprecations = classified_diff.get("classification_summary", {}).get("deprecations", 0)
        
        if breaking > 0:
            status = "critical"
        elif deprecations > 0:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "last_sync": classified_diff.get("classified_at"),
            "changes_count": classified_diff.get("classification_summary", {}).get("total_changes", 0),
            "breaking_count": breaking
        }
    
    # Get URLs for vendor (docs, openapi, changelog)
    def _get_vendor_urls(self, vendor: str) -> Dict[str, Optional[str]]:

        # Load from discovery snapshot
        discovery_file = self.storage_dir / "discovery" / f"{vendor}.json"
        
        if not discovery_file.exists():
            return {"docs": None, "openapi": None, "changelog": None}
        
        with open(discovery_file, 'r') as f:
            discovery = json.load(f)
        
        sources = discovery.get("sources", {})
        
        return {
            "docs": sources.get("docs"),
            "openapi": sources.get("openapi"),
            "changelog": sources.get("changelog")
        }
    
    # Get recent changes across all vendors
    def get_recent_changes(self, limit: int = 20, vendor: Optional[str] = None) -> List[Dict[str, Any]]:

        changes = []
        
        # Determine which vendors to scan
        if vendor:
            vendors_to_scan = [vendor]
        else:
            vendors_to_scan = [v["name"] for v in self.get_all_vendors()]
        
        # Scan classified diffs
        for vendor_name in vendors_to_scan:
            classified_dir = self.storage_dir / "classified_diffs" / vendor_name
            
            if not classified_dir.exists():
                continue
            
            # Get all classified diffs (last 5 per vendor)
            classified_files = sorted(classified_dir.glob("classified_diff_*.json"), reverse=True)[:5]
            
            for classified_file in classified_files:
                with open(classified_file, 'r') as f:
                    classified_diff = json.load(f)
                
                # Extract each change
                for change in classified_diff.get("classified_changes", []):
                    changes.append({
                        "vendor": vendor_name,
                        "classified_at": classified_diff["classified_at"],
                        "endpoint_id": change["endpoint_id"],
                        "path": change["path"],
                        "method": change["method"],
                        "change_type": change["change_type"],
                        "severity": change["classification"]["severity"],
                        "confidence": change["classification"]["confidence"],
                        "reasoning": change["classification"]["reasoning"],
                        "recommended_action": change["classification"]["recommended_action"],
                        "migration_path": change["classification"].get("migration_path"),
                        "impact": change["classification"]["estimated_impact"]
                    })
        
        # Sort by timestamp (newest first)
        changes.sort(key=lambda x: x["classified_at"], reverse=True)
        
        return changes[:limit]
    
    # Get detailed info for a specific vendor
    def get_vendor_detail(self, vendor: str) -> Optional[Dict[str, Any]]:

        # Get basic vendor info
        all_vendors = self.get_all_vendors()
        vendor_info = next((v for v in all_vendors if v["name"] == vendor), None)
        
        if not vendor_info:
            return None
        
        # Get versions (normalized snapshots)
        versions = self._get_vendor_versions(vendor)
        
        # Get all changes for this vendor
        changes = self.get_recent_changes(limit=100, vendor=vendor)
        
        # Get endpoint count
        endpoint_count = self._get_endpoint_count(vendor)
        
        return {
            **vendor_info,
            "versions": versions,
            "changes": changes,
            "endpoint_count": endpoint_count
        }
    
    # Get all normalized snapshots for a vendor
    def _get_vendor_versions(self, vendor: str) -> List[Dict[str, Any]]:

        normalized_dir = self.storage_dir / "normalized" / vendor
        
        if not normalized_dir.exists():
            return []
        
        snapshots_dir = normalized_dir / "snapshots"
        
        if not snapshots_dir.exists():
            return []
        
        # Get baseline and latest symlink targets
        baseline_path = normalized_dir / "baseline.json"
        latest_path = normalized_dir / "latest.json"
        
        baseline_target = baseline_path.resolve().name if baseline_path.exists() else None
        latest_target = latest_path.resolve().name if latest_path.exists() else None
        
        # List all snapshots
        snapshot_files = sorted(snapshots_dir.glob("*.json"), reverse=True)
        
        versions = []
        for snapshot_file in snapshot_files:
            filename = snapshot_file.name
            
            versions.append({
                "timestamp": filename.replace(".json", ""),
                "filename": filename,
                "is_baseline": filename == baseline_target,
                "is_latest": filename == latest_target
            })
        
        return versions
    
    # Get total number of endpoints for vendor
    def _get_endpoint_count(self, vendor: str) -> int:

        # Load latest normalized snapshot
        normalized_dir = self.storage_dir / "normalized" / vendor
        latest_path = normalized_dir / "latest.json"
        
        if not latest_path.exists():
            return 0
        
        with open(latest_path, 'r') as f:
            normalized = json.load(f)
        
        return len(normalized.get("endpoints", []))
    
    # Get aggregated stats for dashboard
    def get_dashboard_stats(self) -> Dict[str, Any]:

        vendors = self.get_all_vendors()
        changes = self.get_recent_changes(limit=1000)  # Get all recent
        
        # Count by severity
        severity_counts = defaultdict(int)
        for change in changes:
            severity_counts[change["severity"]] += 1
        
        # Count vendors by status
        status_counts = defaultdict(int)
        for vendor in vendors:
            status_counts[vendor["status"]] += 1
        
        return {
            "total_vendors": len(vendors),
            "healthy_vendors": status_counts.get("healthy", 0),
            "warning_vendors": status_counts.get("warning", 0),
            "critical_vendors": status_counts.get("critical", 0),
            "total_changes": len(changes),
            "breaking_changes": severity_counts.get("breaking", 0),
            "deprecations": severity_counts.get("deprecation", 0),
            "additive_changes": severity_counts.get("additive", 0),
            "minor_changes": severity_counts.get("minor", 0)
        }
