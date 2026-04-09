"""
Cache management API routes.
"""

from flask import Blueprint, jsonify
from specwatch.cache.cache_manager import CacheManager
from specwatch.cache.cache_metrics import get_cache_metrics

bp = Blueprint('cache', __name__, url_prefix='/api/cache')


# Get cache statistics
@bp.route('/stats', methods=['GET'])
def get_stats():

    cache_manager = CacheManager()
    metrics = get_cache_metrics()
    
    stats = cache_manager.get_stats()
    metrics_summary = metrics.get_summary()
    
    return jsonify({
        "cache": stats,
        "metrics": metrics_summary
    })


# Clear entire cache
@bp.route('/clear', methods=['POST'])
def clear_cache():

    cache_manager = CacheManager()
    cache_manager.clear_all()
    
    return jsonify({
        "success": True,
        "message": "Cache cleared successfully"
    })


# Invalidate cache for specific vendor
@bp.route('/vendor/<vendor>/invalidate', methods=['POST'])
def invalidate_vendor(vendor):

    cache_manager = CacheManager()
    cache_manager.invalidate_vendor(vendor)
    
    return jsonify({
        "success": True,
        "message": f"Cache invalidated for vendor: {vendor}"
    })


# Get cache info for specific vendor
@bp.route('/vendor/<vendor>/info', methods=['GET'])
def vendor_cache_info(vendor):

    cache_manager = CacheManager()
    info = cache_manager.get_vendor_cache_info(vendor)
    
    return jsonify(info)
