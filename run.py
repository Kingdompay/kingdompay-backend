"""
Development server runner
"""

from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    # Default to 5001 to avoid conflict with macOS AirPlay on port 5000
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(port=port, debug=debug)
