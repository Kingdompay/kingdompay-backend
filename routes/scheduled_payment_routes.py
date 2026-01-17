"""
Scheduled Payment routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal
from datetime import datetime
from routes import api_v1_bp
from services.scheduled_payment_service import ScheduledPaymentService

scheduled_service = ScheduledPaymentService()


@api_v1_bp.route("/scheduled-payments", methods=["POST"])
@jwt_required()
def create_scheduled_payment():
    """
    Create a scheduled/recurring payment
    ---
    tags:
      - Scheduled Payments
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - amount
            - frequency
          properties:
            amount:
              type: number
              example: 1000
            frequency:
              type: string
              enum: [daily, weekly, biweekly, monthly, quarterly, yearly]
              example: "monthly"
            recipient_wallet_id:
              type: integer
              description: For internal transfers
            recipient_phone:
              type: string
              description: For M-Pesa payments
              example: "0712345678"
            description:
              type: string
              example: "Monthly savings"
            start_date:
              type: string
              format: date-time
            end_date:
              type: string
              format: date-time
            max_runs:
              type: integer
              description: Maximum number of payments
    responses:
      201:
        description: Scheduled payment created
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        amount = data.get("amount")
        frequency = data.get("frequency")
        
        if not amount or not frequency:
            return jsonify({
                "success": False,
                "message": "amount and frequency are required"
            }), 400

        result = scheduled_service.create_scheduled_payment(
            user_id=int(user_id),
            amount=Decimal(str(amount)),
            frequency=frequency,
            recipient_wallet_id=data.get("recipient_wallet_id"),
            recipient_phone=data.get("recipient_phone"),
            description=data.get("description"),
            start_date=datetime.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            max_runs=data.get("max_runs")
        )

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/scheduled-payments", methods=["GET"])
@jwt_required()
def list_scheduled_payments():
    """
    List user's scheduled payments
    ---
    tags:
      - Scheduled Payments
    security:
      - Bearer: []
    parameters:
      - in: query
        name: active_only
        type: boolean
        default: true
    responses:
      200:
        description: List of scheduled payments
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        active_only = request.args.get("active_only", "true").lower() == "true"
        
        payments = scheduled_service.get_user_scheduled_payments(
            user_id=int(user_id),
            active_only=active_only
        )
        
        return jsonify({
            "success": True,
            "scheduled_payments": payments
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/scheduled-payments/<int:payment_id>", methods=["PUT"])
@jwt_required()
def update_scheduled_payment(payment_id):
    """
    Update a scheduled payment
    ---
    tags:
      - Scheduled Payments
    security:
      - Bearer: []
    parameters:
      - in: path
        name: payment_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            amount:
              type: number
            description:
              type: string
            frequency:
              type: string
            is_active:
              type: boolean
    responses:
      200:
        description: Payment updated
      404:
        description: Payment not found
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result = scheduled_service.update_scheduled_payment(
            payment_id=payment_id,
            user_id=int(user_id),
            **data
        )

        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/scheduled-payments/<int:payment_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_scheduled_payment(payment_id):
    """
    Cancel a scheduled payment
    ---
    tags:
      - Scheduled Payments
    security:
      - Bearer: []
    parameters:
      - in: path
        name: payment_id
        type: integer
        required: true
    responses:
      200:
        description: Payment cancelled
      404:
        description: Payment not found
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        success = scheduled_service.cancel_scheduled_payment(payment_id, int(user_id))
        
        if success:
            return jsonify({
                "success": True,
                "message": "Scheduled payment cancelled"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Scheduled payment not found"
            }), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
