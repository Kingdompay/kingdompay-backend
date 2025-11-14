"""
KingdomPay Flask Application
Phase 1: Wallets + Communities + Giving
"""

import os
import json
import uuid
from flask import Flask, request, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import Config
from extensions import db, migrate, jwt, mail, limiter, redis_client, cache_service
from routes import api_v1_bp
from services.ledger_service import LedgerService
from services.encryption_service import EncryptionService
from services.health_service import HealthService
from services.kyc_service import KYCService
from services.security_service import SecurityMiddleware
from models import User, Wallet, Transaction, OTPVerification


load_dotenv()


def create_app(config_class=Config):
    """Application factory pattern"""
    # Configure template and static folders
    app = Flask(
        __name__,
        template_folder="static",
        static_folder="static",
        static_url_path="/static",
    )
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

    # Initialize system wallets on startup
    with app.app_context():
        from services.wallet_service import WalletService

        try:
            WalletService.initialize_system_wallets()
        except Exception as e:
            app.logger.warning(f"Could not initialize system wallets: {e}")

    # Initialize security middleware
    SecurityMiddleware(app)

    # Register blueprints
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # Request ID and JSON logging
    @app.before_request
    def add_request_id_and_log():
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = req_id  # type: ignore[attr-defined]
        # Minimal JSON access log
        app.logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                    "request_id": req_id,
                }
            )
        )

    @app.after_request
    def set_request_id_header(resp):
        req_id = getattr(request, "request_id", None)
        if req_id:
            resp.headers["X-Request-ID"] = req_id
        return resp

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

    @app.route("/communities-demo")
    def communities_demo():
        """Communities dashboard demo"""
        try:
            return render_template("communities.html")
        except:
            return "Communities demo template not found"

    @app.route("/campaigns-demo")
    def campaigns_demo():
        """Campaigns dashboard demo"""
        try:
            return render_template("campaigns.html")
        except:
            return "Campaigns demo template not found"

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Basic health check endpoint"""
        return {"status": "healthy", "service": "kingdompay-api", "version": "1.0.0"}

    # Ready endpoint (explicit DB and Redis check)
    @app.route("/ready")
    def ready_check():
        return app.health_service.get_readiness()

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

    # Metrics endpoint (basic placeholder)
    @app.route("/metrics")
    def metrics():
        return (
            'kingdompay_app_info{version="1.0.0"} 1\n',
            200,
            {"Content-Type": "text/plain; version=0.0.4"},
        )

    # Error handlers
    # JWT error handlers for consistent JSON responses
    @jwt.unauthorized_loader
    def handle_missing_jwt(reason):
        return {
            "error": True,
            "message": "Missing or invalid authorization token",
            "code": "JWT_MISSING",
            "details": {"reason": reason},
        }, 401

    @jwt.invalid_token_loader
    def handle_invalid_jwt(reason):
        return {
            "error": True,
            "message": "Invalid token",
            "code": "JWT_INVALID",
            "details": {"reason": reason},
        }, 401

    @jwt.expired_token_loader
    def handle_expired_jwt(jwt_header, jwt_payload):
        return {
            "error": True,
            "message": "Token has expired",
            "code": "JWT_EXPIRED",
        }, 401

    @jwt.needs_fresh_token_loader
    def handle_needs_fresh_jwt(jwt_header, jwt_payload):
        return {
            "error": True,
            "message": "Fresh token required",
            "code": "JWT_FRESH_REQUIRED",
        }, 401

    @jwt.revoked_token_loader
    def handle_revoked_jwt(jwt_header, jwt_payload):
        return {
            "error": True,
            "message": "Token has been revoked",
            "code": "JWT_REVOKED",
        }, 401

    @app.errorhandler(400)
    def bad_request(error):
        return {"error": True, "message": "Bad request", "code": "BAD_REQUEST"}, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {
            "error": True,
            "message": "Authentication required",
            "code": "UNAUTHORIZED",
        }, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {
            "error": True,
            "message": "Insufficient permissions",
            "code": "FORBIDDEN",
        }, 403

    @app.errorhandler(404)
    def not_found(error):
        return {
            "error": True,
            "message": "Resource not found",
            "code": "NOT_FOUND",
        }, 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {
            "error": True,
            "message": "Request too large",
            "code": "REQUEST_TOO_LARGE",
        }, 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return {
            "error": True,
            "message": "Too many requests",
            "code": "RATE_LIMIT_EXCEEDED",
        }, 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {
            "error": True,
            "message": "Internal server error",
            "code": "INTERNAL_ERROR",
        }, 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        db.session.rollback()
        app.logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        return {
            "error": True,
            "message": "An unexpected error occurred",
            "code": "UNEXPECTED_ERROR",
        }, 500

    return app


# Create app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5040)
