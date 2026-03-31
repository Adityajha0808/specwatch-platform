"""
Vendor management routes.
Handles vendor CRUD operations, version listing, baseline updates.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from app.utils.data_loader import DataLoader
import subprocess
import json
import shutil
import sys
from pathlib import Path

bp = Blueprint('vendors', __name__, url_prefix='/vendors')


# Vendor management page
@bp.route('/')
def vendors_list():

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    vendors = loader.get_all_vendors()
    
    return render_template(
        'vendors_list.html',
        vendors=vendors
    )


# API: Get all vendors
@bp.route('/api/list')
def api_list():

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    vendors = loader.get_all_vendors()
    
    return jsonify(vendors)


# API: Add new vendor
@bp.route('/api/add', methods=['POST'])
def api_add():

    data = request.json
    
    # Required fields
    name = data.get('name')
    display_name = data.get('display_name')
    
    if not name:
        return jsonify({"error": "Vendor name & ID required"}), 400
    
    if not display_name:
        return jsonify({"error": "Vendor display name required"}), 400
    
    try:
        # Call add_vendor.py script
        result = subprocess.run(
            ["python", 'scripts/add_vendor.py', name, display_name or name],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            return jsonify({"success": True, "message": f"Vendor {name} added"})
        else:
            return jsonify({"error": result.stderr}), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Add vendor script timed out"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API: Remove vendor from configuration
@bp.route('/api/<vendor>/remove', methods=['POST'])
def api_remove(vendor):
    
    # Get clean_storage flag from request
    data = request.get_json() or {}
    clean_storage = data.get('clean_storage', False)
    
    try:
        config_dir = Path("specwatch/config/json")
        vendors_path = config_dir / "vendors.json"
        registry_path = config_dir / "vendor_registry.json"
        specs_path = config_dir / "vendor_specs.json"
        
        removed_count = 0
        
        # Remove from vendors.json
        if vendors_path.exists():
            with open(vendors_path, 'r') as f:
                vendors_config = json.load(f)
            
            original_count = len(vendors_config.get("vendors", []))
            vendors_config["vendors"] = [
                v for v in vendors_config.get("vendors", []) 
                if v["name"] != vendor
            ]
            
            if len(vendors_config["vendors"]) < original_count:
                with open(vendors_path, 'w') as f:
                    json.dump(vendors_config, f, indent=2)
                    f.write("\n")
                removed_count += 1
        
        # Remove from vendor_registry.json
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry_config = json.load(f)
            
            if vendor in registry_config.get("vendors", {}):
                del registry_config["vendors"][vendor]
                with open(registry_path, 'w') as f:
                    json.dump(registry_config, f, indent=2)
                    f.write("\n")
                removed_count += 1
        
        # Remove from vendor_specs.json
        if specs_path.exists():
            with open(specs_path, 'r') as f:
                specs_config = json.load(f)
            
            if vendor in specs_config:
                del specs_config[vendor]
                with open(specs_path, 'w') as f:
                    json.dump(specs_config, f, indent=2)
                    f.write("\n")
                removed_count += 1
        
        # Clean storage if requested
        storage_cleaned = []
        if clean_storage:
            storage_base = current_app.config['STORAGE_DIR']
            
            # Storage locations to clean
            locations = [
                storage_base / "discovery" / f"{vendor}.json",
                storage_base / "raw" / "raw_discovery",
                storage_base / "raw" / "raw_specs",
                storage_base / "normalized" / vendor,
                storage_base / "diffs" / vendor,
                storage_base / "classified_diffs" / vendor,
                storage_base / "alerts" / f"{vendor}_alert_history.json"
            ]
            
            for location in locations:
                if location.exists():
                    if location.is_file():
                        location.unlink()
                        storage_cleaned.append(str(location))
                    elif location.is_dir():
                        shutil.rmtree(location)
                        storage_cleaned.append(str(location))
            
            # Clean vendor-specific files in raw directories
            for pattern in [f"{vendor}_*.json", f"{vendor}_openapi_*"]:
                for path in [storage_base / "raw" / "raw_discovery", storage_base / "raw" / "raw_specs"]:
                    if path.exists():
                        for file in path.glob(pattern):
                            file.unlink()
                            storage_cleaned.append(str(file))
        
        if removed_count == 0:
            return jsonify({"error": f"Vendor {vendor} not found in configuration"}), 404
        
        return jsonify({
            "success": True,
            "message": f"Vendor {vendor} removed from configuration",
            "removed_from": removed_count,
            "storage_cleaned": len(storage_cleaned),
            "storage_files": storage_cleaned if clean_storage else []
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API: List all versions for vendor
@bp.route('/api/<vendor>/versions')
def api_versions(vendor):

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    vendor_data = loader.get_vendor_detail(vendor)
    
    if not vendor_data:
        return jsonify({"error": "Vendor not found"}), 404
    
    return jsonify(vendor_data['versions'])


# API: Update baseline version
@bp.route('/api/<vendor>/baseline', methods=['PUT'])
def api_update_baseline(vendor):

    data = request.json
    timestamp = data.get('timestamp')
    
    if not timestamp:
        return jsonify({"error": "Timestamp required"}), 400
    
    try:
        # Call update_baseline.py script
        result = subprocess.run(
            ["python", 'scripts/update_baseline.py', vendor, timestamp],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            return jsonify({"success": True, "message": f"Baseline updated to {timestamp}"})
        else:
            return jsonify({"error": result.stderr}), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Update baseline script timed out"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    