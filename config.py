"""
Configuration settings for KingdomPay Flask application
"""

import os
from datetime import timedelta

import secrets


class Config:
    """Base configuration"""

    # Flask Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))
    )

    # Database Configuration
    # If DATABASE_URL is not provided, default to a local SQLite database for development
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'kingdompay.db')}"

    # Handle Render's PostgreSQL URL format
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # Redis Configuration
    REDIS_URL = os.environ.get("REDIS_URL")

    # Security Configuration
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "1000 per hour")

    # External Services
    SMS_PROVIDER_API_KEY = os.environ.get("SMS_PROVIDER_API_KEY")
    SMS_PROVIDER_URL = os.environ.get("SMS_PROVIDER_URL")

    # Email Configuration
    MAIL_SERVER = os.environ.get("EMAIL_SERVER")
    MAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET = os.environ.get("S3_BUCKET")

    # Monitoring
    PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 9090))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Feature Flags
    ENABLE_KYC_TIER_1 = os.environ.get("ENABLE_KYC_TIER_1", "true").lower() == "true"
    ENABLE_KYC_TIER_2 = os.environ.get("ENABLE_KYC_TIER_2", "false").lower() == "true"
    ENABLE_COMMUNITY_CURRENCY = (
        os.environ.get("ENABLE_COMMUNITY_CURRENCY", "false").lower() == "true"
    )

    # Business Rules
    DEFAULT_CURRENCY = "KES"
    MIN_TRANSFER_AMOUNT = 1.0
    MAX_TRANSFER_AMOUNT = 1000000.0
    WALLET_CREATION_LIMIT = 5  # Max wallets per user

    # KYC Tiers
    KYC_TIER_0_LIMIT = 10000.0  # Phone verified
    KYC_TIER_1_LIMIT = 100000.0  # ID verified
    KYC_TIER_2_LIMIT = 1000000.0  # Enhanced verification

    # Guardrails: In production, require critical secrets and disallow SQLite
    APP_ENV = os.environ.get("APP_ENV", "development").lower()
    if APP_ENV == "production":
        required_envs = [
            ("SECRET_KEY", SECRET_KEY),
            ("JWT_SECRET_KEY", JWT_SECRET_KEY),
            ("ENCRYPTION_KEY", os.environ.get("ENCRYPTION_KEY")),
            ("DATABASE_URL", os.environ.get("DATABASE_URL")),
        ]
        missing = [name for name, value in required_envs if not value]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables in production: {', '.join(missing)}"
            )
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
            raise RuntimeError("SQLite is not allowed in production. Set DATABASE_URL.")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
