"""
Flask application entry point.
"""

import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create Flask app instance
app = create_app()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  SpecWatch Dashboard Starting")
    print("="*60)
    print(f"\n  📊 Dashboard: http://localhost:5050")
    print(f"  📁 Storage: {app.config['STORAGE_DIR']}")
    print(f"\n  Press CTRL+C to stop\n")
    print("="*60 + "\n")
    
    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=5050,
        debug=app.config['DEBUG']
    )
