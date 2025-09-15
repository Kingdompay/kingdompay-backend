"""
KingdomPay Flask Application
Phase 1: Wallets + Communities + Giving
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import Config
from extensions import db, migrate, jwt, mail, limiter, redis_client
from api.v1 import api_v1_bp
from services.ledger_service import LedgerService
from services.encryption_service import EncryptionService


load_dotenv()


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    CORS(app)

    # Initialize services
    app.ledger_service = LedgerService()
    app.encryption_service = EncryptionService()

    # Register blueprints
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return {"status": "healthy", "service": "kingdompay-api", "version": "1.0.0"}

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request", "message": str(error)}, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized", "message": "Authentication required"}, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden", "message": "Insufficient permissions"}, 403

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "message": "Resource not found"}, 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return {"error": "Rate limit exceeded", "message": "Too many requests"}, 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        }, 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
