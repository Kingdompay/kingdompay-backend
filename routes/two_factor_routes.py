"""
Two-Factor Authentication routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from routes import api_v1_bp
from services.two_factor_service import TwoFactorService
from services.auth_service import AuthService

tfa_service = TwoFactorService()
auth_service = AuthService()


@api_v1_bp.route("/2fa/status", methods=["GET"])
@jwt_required()
def get_2fa_status():
    """
    Get 2FA status for current user
    ---
    tags:
      - Two-Factor Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: 2FA status
        schema:
          type: object
          properties:
            is_enabled:
              type: boolean
            is_configured:
              type: boolean
            enabled_at:
              type: string
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        status = tfa_service.get_2fa_status(int(user_id))
        return jsonify({"success": True, **status}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/2fa/setup", methods=["POST"])
@jwt_required()
def setup_2fa():
    """
    Setup 2FA - generates secret and QR code
    ---
    tags:
      - Two-Factor Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: 2FA setup data
        schema:
          type: object
          properties:
            success:
              type: boolean
            secret:
              type: string
              description: TOTP secret (save as backup)
            qr_code:
              type: string
              description: Base64 QR code image
            backup_codes:
              type: array
              items:
                type: string
      400:
        description: 2FA already enabled
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        user = auth_service.get_current_user()
        
        result = tfa_service.setup_2fa(
            user_id=int(user_id),
            user_email=user.email if user else None
        )

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/2fa/verify", methods=["POST"])
@jwt_required()
def verify_and_enable_2fa():
    """
    Verify code and enable 2FA
    ---
    tags:
      - Two-Factor Authentication
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - code
          properties:
            code:
              type: string
              description: 6-digit code from authenticator app
              example: "123456"
    responses:
      200:
        description: 2FA enabled successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            backup_codes:
              type: array
              items:
                type: string
              description: Save these codes securely!
      400:
        description: Invalid code
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        code = data.get("code")

        if not code:
            return jsonify({
                "success": False,
                "message": "Verification code is required"
            }), 400

        result = tfa_service.verify_and_enable(int(user_id), code)

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/2fa/disable", methods=["POST"])
@jwt_required()
def disable_2fa():
    """
    Disable 2FA (requires valid code)
    ---
    tags:
      - Two-Factor Authentication
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - code
          properties:
            code:
              type: string
              description: 6-digit code or backup code
    responses:
      200:
        description: 2FA disabled
      400:
        description: Invalid code
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        code = data.get("code")

        if not code:
            return jsonify({
                "success": False,
                "message": "Verification code is required"
            }), 400

        result = tfa_service.disable_2fa(int(user_id), code)

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/2fa/backup-codes", methods=["POST"])
@jwt_required()
def regenerate_backup_codes():
    """
    Regenerate backup codes (requires valid 2FA code)
    ---
    tags:
      - Two-Factor Authentication
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - code
          properties:
            code:
              type: string
              description: Current 6-digit code
    responses:
      200:
        description: New backup codes generated
        schema:
          type: object
          properties:
            success:
              type: boolean
            backup_codes:
              type: array
              items:
                type: string
      400:
        description: Invalid code
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        code = data.get("code")

        if not code:
            return jsonify({
                "success": False,
                "message": "Verification code is required"
            }), 400

        result = tfa_service.regenerate_backup_codes(int(user_id), code)

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
