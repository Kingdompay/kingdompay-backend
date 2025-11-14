"""
Risk and AML routes for transaction risk checks
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.risk_service import RiskService
from decimal import Decimal


auth_service = AuthService()
risk_service = RiskService()


@api_v1_bp.route("/risk/check-transaction", methods=["POST"])
@jwt_required()
def check_transaction_risk():
    """Check transaction risk before execution"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        wallet_id = data.get("wallet_id")
        amount = data.get("amount")
        destination = data.get("destination")  # phone, email, wallet_id

        if not wallet_id or not amount:
            return (
                jsonify(
                    {"success": False, "message": "wallet_id and amount are required"}
                ),
                400,
            )

        result = risk_service.check_transaction_risk(
            user_id=user.id,
            wallet_id=wallet_id,
            amount=Decimal(str(amount)),
            destination=destination,
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/risk/blacklist/check", methods=["POST"])
@jwt_required()
def check_blacklist():
    """Check if entity is blacklisted"""
    try:
        data = request.get_json() or {}
        entity_type = data.get("entity_type")  # PHONE|EMAIL|WALLET|USER
        entity_value = data.get("entity_value")

        if not entity_type or not entity_value:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "entity_type and entity_value are required",
                    }
                ),
                400,
            )

        is_blacklisted = risk_service.check_blacklist(entity_type, entity_value)

        return (
            jsonify(
                {
                    "success": True,
                    "is_blacklisted": is_blacklisted,
                    "entity_type": entity_type,
                    "entity_value": entity_value,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/risk/aml-cases", methods=["GET"])
@jwt_required()
def get_aml_cases():
    """Get AML cases (admin only)"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        status = request.args.get("status")
        user_id = request.args.get("user_id", type=int)

        cases = risk_service.get_aml_cases(status=status, user_id=user_id)

        return (
            jsonify(
                {
                    "success": True,
                    "cases": cases,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
