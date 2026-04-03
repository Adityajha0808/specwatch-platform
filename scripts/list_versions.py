#!/usr/bin/env python
""" List all normalized versions for a vendor """

import json
from pathlib import Path
from datetime import datetime, UTC
import sys


def list_versions(vendor: str):

    snapshots_dir = Path(f"storage/normalized/{vendor}")
    
    if not snapshots_dir.exists():
        print(f"No snapshots found for {vendor}")
        return
    
    snapshots = sorted(snapshots_dir.glob("*.json"))
    
    print(f"\n=== {vendor.upper()} Versions ===")
    print(f"Total snapshots: {len(snapshots)}\n")
    
    for i, snapshot in enumerate(snapshots, 1):
        with open(snapshot) as f:
            data = json.load(f)
        
        timestamp = data['metadata']['normalized_at']
        endpoint_count = len(data['endpoints'])
        source_hash = data['metadata']['source_hash']
        
        print(f"{i}. {snapshot.name}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Endpoints: {endpoint_count}")
        print(f"   Hash: {source_hash}")
        
        # Show if this is baseline or latest
        baseline_link = Path(f"storage/normalized/{vendor}/baseline.json")
        latest_link = Path(f"storage/normalized/{vendor}/latest.json")
        
        markers = []
        if baseline_link.exists() and baseline_link.resolve() == snapshot:
            markers.append("BASELINE")
        if latest_link.exists() and latest_link.resolve() == snapshot:
            markers.append("LATEST")
        
        if markers:
            print(f"   [{' | '.join(markers)}]")
        
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/list_versions.py <vendor>")
        print("Example: python scripts/list_versions.py stripe")
        sys.exit(1)
    
    list_versions(sys.argv[1])
