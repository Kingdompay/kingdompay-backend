"""
API v1 package for KingdomPay
"""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Import all route modules
from . import (
    auth_routes,
    wallet_routes,
    kyc_routes,
    communities_routes,
    campaigns_routes,
    reports_routes,
    webhooks_routes,
    payments_routes,
    payouts_routes,
    reconciliation_routes,
    checkout_routes,
    fees_routes,
    multisig_routes,
    risk_routes,
    mpesa_routes,
    notification_routes,
    scheduled_payment_routes,
    two_factor_routes,
    currency_routes,
)
