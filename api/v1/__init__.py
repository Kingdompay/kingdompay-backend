"""
API v1 package for KingdomPay
"""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Import all route modules
from . import auth_routes, wallet_routes, kyc_routes
