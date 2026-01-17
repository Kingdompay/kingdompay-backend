"""
Authentication routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from routes import api_v1_bp
from services.auth_service import AuthService
from extensions import limiter
from flasgger import swag_from
from swagger_config import AUTH_OTP_REQUEST_SPEC, AUTH_OTP_VERIFY_SPEC, AUTH_ME_SPEC

auth_service = AuthService()


@api_v1_bp.route("/auth/otp/request", methods=["POST", "OPTIONS"])
@limiter.limit("10 per minute;30 per hour")
def request_otp():
    """
    Send OTP to phone number for authentication
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - phone_number
          properties:
            phone_number:
              type: string
              description: Phone number (+254XXXXXXXXX or 07XXXXXXXX)
              example: "+254712345678"
    responses:
      200:
        description: OTP sent successfully
      400:
        description: Invalid phone number
      429:
        description: Rate limit exceeded
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 200
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
        # Log the actual error for debugging
        import traceback
        from flask import current_app
        current_app.logger.error(f"Error in request_otp: {str(e)}\n{traceback.format_exc()}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"An error occurred while processing your request: {str(e)}",
                }
            ),
            500,
        )


@api_v1_bp.route("/auth/otp/verify", methods=["POST"])
@limiter.limit("10 per minute")
def verify_otp():
    """
    Verify OTP and get JWT tokens
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - phone_number
            - otp_code
          properties:
            phone_number:
              type: string
              example: "+254712345678"
            otp_code:
              type: string
              example: "123456"
            full_name:
              type: string
              description: Required for new users
              example: "John Doe"
    responses:
      200:
        description: OTP verified, tokens returned
      401:
        description: Invalid or expired OTP
    """
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
        full_name = data.get("full_name")  # Required for new users
        email = data.get("email")  # Required for new users

        result = auth_service.verify_otp(phone_number, otp_code, full_name, email)

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
    """
    Get current user information
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: User information
        schema:
          type: object
          properties:
            success:
              type: boolean
            user:
              type: object
      401:
        description: Unauthorized
    """
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
