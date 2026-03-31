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
    
    try:
        runner.run_discovery()
        return jsonify({"success": True, "message": "Discovery pipeline started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger ingestion → normalization → diff → classification
@bp.route('/analysis', methods=['POST'])
def trigger_analysis():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    try:
        runner.run_analysis()
        return jsonify({"success": True, "message": "Analysis pipeline started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger full pipeline (all stages)
@bp.route('/full', methods=['POST'])
def trigger_full():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    try:
        runner.run_full_pipeline()
        return jsonify({"success": True, "message": "Full pipeline started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Trigger alerting pipeline
@bp.route('/alerting', methods=['POST'])
def trigger_alerting():

    runner = get_pipeline_runner()
    
    if runner.is_running():
        return jsonify({"error": "Pipeline already running"}), 409
    
    try:
        runner.run_alerting()
        return jsonify({"success": True, "message": "Alerting pipeline started"})
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
