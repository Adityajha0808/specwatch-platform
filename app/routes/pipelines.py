"""
Pipeline control routes.
Handles triggering pipelines from UI.
"""

from flask import Blueprint, request, jsonify
from app.utils.pipeline_runner import get_pipeline_runner

bp = Blueprint('pipelines', __name__, url_prefix='/api/pipelines')


# Trigger discovery pipeline
@bp.route('/discovery', methods=['POST'])
def trigger_discovery():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    # Get vendor from request body
    data = request.get_json() or {}
    vendor = data.get('vendor')
    
    try:
        runner.run_discovery(vendor=vendor)
        msg = f"Discovery pipeline started for {vendor}" if vendor else "Discovery pipeline started for all vendors"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger ingestion → normalization → diff → classification
@bp.route('/analysis', methods=['POST'])
def trigger_analysis():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    # Get vendor from request body
    data = request.get_json() or {}
    vendor = data.get('vendor')
    
    try:
        runner.run_analysis(vendor=vendor)
        msg = f"Analysis pipeline started for {vendor}" if vendor else "Analysis pipeline started for all vendors"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger full pipeline (all stages)
@bp.route('/full', methods=['POST'])
def trigger_full():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    # Get vendor from request body
    data = request.get_json() or {}
    vendor = data.get('vendor')
    
    try:
        runner.run_full_pipeline(vendor=vendor)
        msg = f"Full pipeline started for {vendor}" if vendor else "Full pipeline started for all vendors"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger alerting pipeline
@bp.route('/alerting', methods=['POST'])
def trigger_alerting():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    # Get vendor from request body
    data = request.get_json() or {}
    vendor = data.get('vendor')
    
    try:
        runner.run_alerting(vendor=vendor)
        msg = f"Alerting pipeline started for {vendor}" if vendor else "Alerting pipeline started for all vendors"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get current pipeline status
@bp.route('/status', methods=['GET'])
def get_status():

    runner = get_pipeline_runner()
    return jsonify(runner.get_status())


# Reset pipeline status (for emergency use)
@bp.route('/reset', methods=['POST'])
def reset_status():

    runner = get_pipeline_runner()
    runner.reset()
    return jsonify({"success": True, "message": "Pipeline status reset"})
