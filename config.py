"""
Flask application configuration.
Loads settings from environment variables and defines paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


class Config:
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # Project paths
    BASE_DIR = Path(__file__).parent
    STORAGE_DIR = BASE_DIR / 'storage'
    
    # GitHub integration
    GITHUB_ENABLED = os.getenv('GITHUB_ENABLED', 'true').lower() == 'true'
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    GITHUB_REPO = os.getenv('GITHUB_REPO', 'Adityajha0808/specwatch-alerts')
    
    # Email integration (Gmail SMTP)
    EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    EMAIL_FROM = os.getenv('EMAIL_FROM', os.getenv('SMTP_USERNAME'))
    EMAIL_TO = os.getenv('EMAIL_TO', os.getenv('SMTP_USERNAME'))
    
    # Slack integration (disabled by default - optional)
    SLACK_ENABLED = os.getenv('SLACK_ENABLED', 'false').lower() == 'true'
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#api-alerts')
    
    # Groq API
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Validate required configuration.
    @staticmethod
    def validate():

        warnings = []
        
        if Config.GITHUB_ENABLED and not Config.GITHUB_TOKEN:
            warnings.append("⚠️  GITHUB_TOKEN not set - GitHub alerts disabled")
        
        if Config.EMAIL_ENABLED:
            if not Config.SMTP_USERNAME:
                warnings.append("⚠️  SMTP_USERNAME not set - Email alerts disabled")
            if not Config.SMTP_PASSWORD:
                warnings.append("⚠️  SMTP_PASSWORD not set - Email alerts disabled")
        
        if warnings:
            print("\nConfiguration Warnings:")
            for warning in warnings:
                print(f"  {warning}")
            print("\nSet these in your .env file to enable full functionality.\n")
        
        return True


# Validate on import
Config.validate()
