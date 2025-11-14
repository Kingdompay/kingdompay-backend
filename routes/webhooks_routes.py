"""
Webhook registration routes (MVP)
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.rbac import is_community_admin
from extensions import db
from models.webhook import Webhook


auth_service = AuthService()


@api_v1_bp.route("/webhooks", methods=["POST"])
@jwt_required()
def register_webhook():
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        data = request.get_json() or {}
        community_id = data.get("community_id")
        url = data.get("url")
        secret = data.get("secret")
        if not community_id or not url or not secret:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "community_id, url, secret are required",
                    }
                ),
                400,
            )
        if not is_community_admin(user.id, community_id):
            return jsonify({"success": False, "message": "Forbidden"}), 403
        hook = Webhook(community_id=community_id, url=url, secret=secret)
        db.session.add(hook)
        db.session.commit()
        return jsonify({"success": True, "webhook_id": hook.id}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to register webhook"}), 500
