"""
Authentication routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from api.v1 import api_v1_bp
from services.auth_service import AuthService
from extensions import limiter

auth_service = AuthService()


@api_v1_bp.route("/auth/otp/request", methods=["POST"])
@limiter.limit("5 per minute")
def request_otp():
    """Request OTP for phone number verification"""
    try:
        data = request.get_json()

        if not data or "phone_number" not in data:
            return (
                jsonify({"success": False, "message": "Phone number is required"}),
                400,
            )

        phone_number = data["phone_number"]
        result = auth_service.send_otp(phone_number)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/otp/verify", methods=["POST"])
@limiter.limit("10 per minute")
def verify_otp():
    """Verify OTP and authenticate user"""
    try:
        data = request.get_json()

        if not data or "phone_number" not in data or "otp_code" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Phone number and OTP code are required",
                    }
                ),
                400,
            )

        phone_number = data["phone_number"]
        otp_code = data["otp_code"]
        full_name = data.get("full_name")  # Optional for existing users

        result = auth_service.verify_otp(phone_number, otp_code, full_name)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """Refresh access token"""
    try:
        result = auth_service.refresh_token()

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        return jsonify({"success": True, "user": user.to_dict()}), 200

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        result = auth_service.update_profile(user_id, data)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/logout", methods=["POST"])
@jwt_required()
def logout():
    """Logout user"""
    try:
        user_id = get_jwt_identity()
        result = auth_service.logout(user_id)

        return jsonify(result), 200

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )
