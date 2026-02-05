"""
Money Request routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone
from decimal import Decimal
from routes import api_v1_bp
from services.auth_service import AuthService
from services.ledger_service import LedgerService
from services.transfer_service import TransferService
from models.money_request import MoneyRequest
from models.user import User
from models.wallet import Wallet
from extensions import db

auth_service = AuthService()
ledger_service = LedgerService()
transfer_service = TransferService()


@api_v1_bp.route("/money-requests", methods=["GET"])
@jwt_required()
def get_money_requests():
    """
    Get money requests for the current user (both sent and received)
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Get query parameters
        request_type = request.args.get("type", "all")  # all, sent, received
        status = request.args.get("status")  # pending, accepted, rejected, etc.
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Build query
        if request_type == "sent":
            query = MoneyRequest.query.filter_by(requester_id=user.id)
        elif request_type == "received":
            query = MoneyRequest.query.filter_by(recipient_id=user.id)
        else:
            # Get both sent and received
            query = MoneyRequest.query.filter(
                (MoneyRequest.requester_id == user.id) | (MoneyRequest.recipient_id == user.id)
            )

        if status:
            query = query.filter_by(status=status)

        requests = query.order_by(MoneyRequest.created_at.desc()).limit(limit).offset(offset).all()

        return jsonify({
            "success": True,
            "requests": [req.to_dict() for req in requests],
            "count": len(requests)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/money-requests", methods=["POST"])
@jwt_required()
def create_money_request():
    """
    Create a new money request
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Check if user is KYC verified
        if not auth_service.is_user_kyc_verified(user):
            return jsonify({
                "success": False,
                "message": "KYC verification is required to request money. Please complete your identity verification first."
            }), 403

        data = request.get_json() or {}
        recipient_phone = data.get("recipient_phone") or data.get("recipient")
        amount = data.get("amount")
        message = data.get("message")
        category = data.get("category", "general")
        due_date = data.get("due_date")

        if not recipient_phone:
            return jsonify({"success": False, "message": "Recipient phone number is required"}), 400

        if not amount:
            return jsonify({"success": False, "message": "Amount is required"}), 400

        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        # Find recipient by phone number
        recipient = User.find_by_phone(recipient_phone)
        if not recipient:
            return jsonify({"success": False, "message": "Recipient not found"}), 404

        if recipient.id == user.id:
            return jsonify({"success": False, "message": "Cannot request money from yourself"}), 400

        # Parse due date if provided
        due_date_datetime = None
        if due_date:
            try:
                due_date_datetime = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                if due_date_datetime < datetime.now(timezone.utc):
                    return jsonify({"success": False, "message": "Due date cannot be in the past"}), 400
            except (ValueError, AttributeError):
                return jsonify({"success": False, "message": "Invalid due date format"}), 400

        # Create money request
        money_request = MoneyRequest(
            requester_id=user.id,
            recipient_id=recipient.id,
            amount=amount_decimal,
            currency=data.get("currency", "KES"),
            message=message,
            category=category,
            due_date=due_date_datetime,
            status="pending"
        )

        db.session.add(money_request)
        db.session.commit()

        return jsonify({
            "success": True,
            "request": money_request.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/money-requests/<int:request_id>/accept", methods=["POST"])
@jwt_required()
def accept_money_request(request_id):
    """
    Accept a money request and transfer funds
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        money_request = MoneyRequest.query.get(request_id)
        if not money_request:
            return jsonify({"success": False, "message": "Money request not found"}), 404

        # Check if user is the recipient
        if money_request.recipient_id != user.id:
            return jsonify({"success": False, "message": "You are not authorized to accept this request"}), 403

        # Check if request can be responded to
        if not money_request.can_be_responded_to():
            return jsonify({
                "success": False,
                "message": f"Request is {money_request.status} and cannot be accepted"
            }), 400

        # Get recipient wallet (the person who will send money)
        recipient_wallet = Wallet.find_by_user_id(user.id)
        if not recipient_wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Check if wallet has sufficient balance
        if recipient_wallet.balance < money_request.amount:
            return jsonify({"success": False, "message": "Insufficient balance"}), 400

        # Get requester wallet (the person who will receive money)
        requester_wallet = Wallet.find_by_user_id(money_request.requester_id)
        if not requester_wallet:
            return jsonify({"success": False, "message": "Requester wallet not found"}), 404

        # Transfer funds from recipient to requester
        idempotency_key = request.headers.get("Idempotency-Key", f"money-request-{request_id}-{datetime.utcnow().timestamp()}")
        
        result = transfer_service.process_transfer(
            from_wallet_id=recipient_wallet.id,
            to_wallet_id=requester_wallet.id,
            amount=money_request.amount,
            description=money_request.message or f"Money request from {money_request.requester.full_name}",
            idempotency_key=idempotency_key
        )

        if not result.get("success"):
            return jsonify({
                "success": False,
                "message": result.get("message", "Failed to process transfer")
            }), 400

        # Update money request status
        money_request.status = "accepted"
        money_request.transaction_id = result.get("transaction_id")
        money_request.responded_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "request": money_request.to_dict(),
            "transaction_id": result.get("transaction_id")
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/money-requests/<int:request_id>/reject", methods=["POST"])
@jwt_required()
def reject_money_request(request_id):
    """
    Reject a money request
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        money_request = MoneyRequest.query.get(request_id)
        if not money_request:
            return jsonify({"success": False, "message": "Money request not found"}), 404

        # Check if user is the recipient
        if money_request.recipient_id != user.id:
            return jsonify({"success": False, "message": "You are not authorized to reject this request"}), 403

        # Check if request can be responded to
        if not money_request.can_be_responded_to():
            return jsonify({
                "success": False,
                "message": f"Request is {money_request.status} and cannot be rejected"
            }), 400

        # Update money request status
        money_request.status = "rejected"
        money_request.responded_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "request": money_request.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500


@api_v1_bp.route("/money-requests/<int:request_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_money_request(request_id):
    """
    Cancel a money request (only requester can cancel)
    """
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        money_request = MoneyRequest.query.get(request_id)
        if not money_request:
            return jsonify({"success": False, "message": "Money request not found"}), 404

        # Check if user is the requester
        if money_request.requester_id != user.id:
            return jsonify({"success": False, "message": "You are not authorized to cancel this request"}), 403

        # Check if request can be cancelled
        if money_request.status != "pending":
            return jsonify({
                "success": False,
                "message": f"Request is {money_request.status} and cannot be cancelled"
            }), 400

        # Update money request status
        money_request.status = "cancelled"
        money_request.responded_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "request": money_request.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your request"
        }), 500
