"""
Notification routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from routes import api_v1_bp
from services.notification_service import NotificationService

notification_service = NotificationService()


@api_v1_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    """
    Get user notifications
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: query
        name: unread_only
        type: boolean
        default: false
      - in: query
        name: limit
        type: integer
        default: 50
      - in: query
        name: offset
        type: integer
        default: 0
    responses:
      200:
        description: List of notifications
        schema:
          type: object
          properties:
            success:
              type: boolean
            notifications:
              type: array
            unread_count:
              type: integer
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        notifications = notification_service.get_user_notifications(
            user_id=int(user_id),
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
        unread_count = notification_service.get_unread_count(int(user_id))

        return jsonify({
            "success": True,
            "notifications": notifications,
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/notifications/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    """
    Get unread notification count
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: Unread count
        schema:
          type: object
          properties:
            success:
              type: boolean
            unread_count:
              type: integer
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        count = notification_service.get_unread_count(int(user_id))
        return jsonify({"success": True, "unread_count": count}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def mark_notification_read(notification_id):
    """
    Mark notification as read
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: path
        name: notification_id
        type: integer
        required: true
    responses:
      200:
        description: Notification marked as read
      404:
        description: Notification not found
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        success = notification_service.mark_as_read(notification_id, int(user_id))
        
        if success:
            return jsonify({"success": True, "message": "Notification marked as read"}), 200
        else:
            return jsonify({"success": False, "message": "Notification not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/notifications/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    """
    Mark all notifications as read
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: All notifications marked as read
        schema:
          type: object
          properties:
            success:
              type: boolean
            count:
              type: integer
              description: Number of notifications marked as read
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        count = notification_service.mark_all_as_read(int(user_id))
        return jsonify({
            "success": True,
            "message": f"{count} notifications marked as read",
            "count": count
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/notifications/register-device", methods=["POST"])
@jwt_required()
def register_device():
    """
    Register device for push notifications
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - fcm_token
          properties:
            fcm_token:
              type: string
              description: Firebase Cloud Messaging token
    responses:
      200:
        description: Device registered
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        fcm_token = data.get("fcm_token")

        if not fcm_token:
            return jsonify({
                "success": False,
                "message": "fcm_token is required"
            }), 400

        success = notification_service.register_fcm_token(int(user_id), fcm_token)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Device registered for push notifications"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Failed to register device"
            }), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
