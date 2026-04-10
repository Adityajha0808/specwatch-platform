"""
Dashboard routes.
Handles main dashboard, vendor details, and changes feed.
"""

from flask import Blueprint, render_template, current_app, jsonify
from app.utils.data_loader import DataLoader

bp = Blueprint('dashboard', __name__)


# Main dashboard page
@bp.route('/')
def index():

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    
    # Get dashboard stats
    stats = loader.get_dashboard_stats()
    vendors = loader.get_all_vendors()
    recent_changes = loader.get_recent_changes(limit=10)
    
    return render_template(
        'dashboard.html',
        stats=stats,
        vendors=vendors,
        recent_changes=recent_changes
    )


# Vendor detail page
@bp.route('/vendors/<vendor>')
def vendor_detail(vendor):

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    
    vendor_data = loader.get_vendor_detail(vendor)
    
    if not vendor_data:
        return "Vendor not found", 404
    
    return render_template(
        'vendor_detail.html',
        vendor=vendor_data
    )


# API endpoint for dashboard stats
@bp.route('/api/stats')
def api_stats():

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    stats = loader.get_dashboard_stats()
    
    return jsonify(stats)


# API endpoint for recent changes
@bp.route('/api/changes')
def api_changes():

    loader = DataLoader(current_app.config['STORAGE_DIR'])
    changes = loader.get_recent_changes(limit=20)
    
    return jsonify(changes)
