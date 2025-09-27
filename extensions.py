"""
Flask extensions initialization
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import redis


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

# Configure Limiter storage; force in-memory for local/dev/test to avoid Redis dependency
ratelimit_storage_url = os.environ.get("RATELIMIT_STORAGE_URL")
app_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).lower()

if ratelimit_storage_url:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=ratelimit_storage_url,
        default_limits=[os.environ.get("RATELIMIT_DEFAULT", "1000 per hour")],
        in_memory_fallback_enabled=True,
        strategy="fixed-window",
    )
else:
    # Explicitly set memory storage to avoid accidental Redis usage
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
        default_limits=[os.environ.get("RATELIMIT_DEFAULT", "1000 per hour")],
        in_memory_fallback_enabled=True,
        strategy="fixed-window",
    )

# Redis client from REDIS_URL or default localhost
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    redis_client = redis.from_url(redis_url, decode_responses=True)
else:
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Initialize cache service
from services.cache_service import CacheService

cache_service = CacheService(redis_client)
