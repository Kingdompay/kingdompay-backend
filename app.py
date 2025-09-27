"""
KingdomPay Flask Application
Phase 1: Wallets + Communities + Giving
"""

import os
from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import Config
from extensions import db, migrate, jwt, mail, limiter, redis_client, cache_service
from api.v1 import api_v1_bp
from services.ledger_service import LedgerService
from services.encryption_service import EncryptionService
from services.health_service import HealthService
from services.kyc_service import KYCService
from models import User, Wallet, Transaction, OTPVerification


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
    app.cache_service = cache_service
    app.health_service = HealthService()
    app.kyc_service = KYCService()

    # Register blueprints
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # Template routes for frontend demos
    @app.route("/")
    def index():
        """Main dashboard template"""
        try:
            return render_template("index.html")
        except:
            return "KingdomPay API is running! Visit /dashboard for the frontend demo."

    @app.route("/dashboard")
    def dashboard():
        """Dashboard template"""
        try:
            return render_template("index.html")
        except:
            return "Dashboard template not found"

    @app.route("/auth-demo")
    def auth_demo():
        """Authentication flow demo"""
        try:
            return render_template("auth.html")
        except:
            return "Auth demo template not found"

    @app.route("/wallet-demo")
    def wallet_demo():
        """Wallet dashboard demo"""
        try:
            return render_template("wallet.html")
        except:
            return "Wallet demo template not found"

    # Health check endpoints
    @app.route("/health")
    def health_check():
        """Basic health check endpoint"""
        return {"status": "healthy", "service": "kingdompay-api", "version": "1.0.0"}

    @app.route("/health/detailed")
    def detailed_health_check():
        """Detailed health check with system metrics"""
        return app.health_service.get_system_health()

    @app.route("/health/ready")
    def readiness_check():
        """Kubernetes readiness probe endpoint"""
        return app.health_service.get_readiness()

    @app.route("/health/live")
    def liveness_check():
        """Kubernetes liveness probe endpoint"""
        return app.health_service.get_liveness()

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
    app.run(debug=True, host="0.0.0.0", port=5001)
