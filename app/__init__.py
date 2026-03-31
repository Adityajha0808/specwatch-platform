"""
Flask application factory.
"""

from flask import Flask
from flask_cors import CORS
from config import Config

# Register blueprints
from app.routes import dashboard, vendors, pipelines, alerts

# Create and configure Flask application
def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(vendors.bp)
    app.register_blueprint(pipelines.bp)
    app.register_blueprint(alerts.bp)
    
    return app
