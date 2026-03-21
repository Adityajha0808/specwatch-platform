#!/usr/bin/env python
"""
Manually update baseline for a vendor.
Usage: python scripts/update_baseline.py stripe 2024-01-15T10:00:00Z
"""

import sys
import json
from pathlib import Path


# Update baseline symlink to point to a specific snapshot.
def update_baseline(vendor: str, snapshot_timestamp: str):

    normalized_dir = Path(f"storage/normalized/{vendor}")
    snapshot_path = normalized_dir / "snapshots" / f"{snapshot_timestamp}.json"
    baseline_link = normalized_dir / "baseline.json"
    
    if not snapshot_path.exists():
        print(f"Snapshot not found: {snapshot_path}")
        return False
    
    # Update symlink
    if baseline_link.exists() or baseline_link.is_symlink():
        baseline_link.unlink()
    
    import os
    relative_target = os.path.relpath(snapshot_path, baseline_link.parent)
    baseline_link.symlink_to(relative_target)
    
    print(f"Baseline updated: {vendor} → {snapshot_timestamp}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/update_baseline.py <vendor> <timestamp>")
        print("Example: python scripts/update_baseline.py stripe 2024-01-15T10:00:00Z")
        sys.exit(1)
    
    update_baseline(sys.argv[1], sys.argv[2])
