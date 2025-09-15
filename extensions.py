"""
Flask extensions initialization
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per hour"])
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
