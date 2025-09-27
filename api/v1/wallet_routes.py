"""
Wallet routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from api.v1 import api_v1_bp
from services.auth_service import AuthService
from models.wallet import Wallet
from models.transaction import Transaction

auth_service = AuthService()


@api_v1_bp.route("/wallets/balance", methods=["GET"])
@jwt_required()
def get_wallet_balance():
    """Get current user's wallet balance"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        return jsonify({"success": True, "wallet": wallet.to_dict()}), 200

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


@api_v1_bp.route("/wallets/transactions", methods=["GET"])
@jwt_required()
def get_wallet_transactions():
    """Get current user's wallet transactions"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        offset = (page - 1) * per_page

        # Get transactions
        transactions = Transaction.get_wallet_transactions(
            wallet.id, limit=per_page, offset=offset
        )

        return (
            jsonify(
                {
                    "success": True,
                    "transactions": [tx.to_dict() for tx in transactions],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "has_more": len(transactions) == per_page,
                    },
                }
            ),
            200,
        )

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


@api_v1_bp.route("/wallets/ledger", methods=["GET"])
@jwt_required()
def get_wallet_ledger():
    """Get wallet ledger (same as transactions for now)"""
    return get_wallet_transactions()


@api_v1_bp.route("/wallets/transfer", methods=["POST"])
@jwt_required()
def transfer_funds():
    """Transfer funds between wallets"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        source_wallet = Wallet.find_by_user_id(user.id)
        if not source_wallet:
            return (
                jsonify({"success": False, "message": "Source wallet not found"}),
                404,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Validate required fields
        required_fields = ["destination_wallet_number", "amount", "description"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify({"success": False, "message": f"{field} is required"}),
                    400,
                )

        destination_wallet_number = data["destination_wallet_number"]
        amount = float(data["amount"])
        description = data["description"]

        # Convert amount to Decimal for consistent arithmetic
        from decimal import Decimal

        amount_decimal = Decimal(str(amount))

        # Validate amount
        if amount <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Check if source wallet has sufficient balance
        if not source_wallet.can_afford(amount_decimal):
            return jsonify({"success": False, "message": "Insufficient funds"}), 400

        # Find destination wallet
        destination_wallet = Wallet.find_by_display_number(destination_wallet_number)
        if not destination_wallet:
            return (
                jsonify({"success": False, "message": "Destination wallet not found"}),
                404,
            )

        # Prevent self-transfer
        if source_wallet.id == destination_wallet.id:
            return (
                jsonify(
                    {"success": False, "message": "Cannot transfer to the same wallet"}
                ),
                400,
            )

        # Perform transfer
        from models.transaction import Transaction
        from extensions import db

        # Create transaction record
        transaction = Transaction(
            source_wallet_id=source_wallet.id,
            destination_wallet_id=destination_wallet.id,
            transaction_type="TRANSFER",
            amount=amount_decimal,
            source_balance_after=source_wallet.balance - amount_decimal,
            destination_balance_after=destination_wallet.balance + amount_decimal,
            description=description,
            status="SUCCESS",
        )

        # Update balances
        source_wallet.balance -= amount_decimal
        destination_wallet.balance += amount_decimal
        source_wallet.updated_at = datetime.now(timezone.utc)
        destination_wallet.updated_at = datetime.now(timezone.utc)

        db.session.add(transaction)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Transfer completed successfully",
                    "transaction": transaction.to_dict(),
                    "source_balance": float(source_wallet.balance),
                    "destination_balance": float(destination_wallet.balance),
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid amount: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/wallets/deposit", methods=["POST"])
@jwt_required()
def deposit_funds():
    """Add funds to wallet (admin/system operation)"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Validate required fields
        if "amount" not in data:
            return jsonify({"success": False, "message": "amount is required"}), 400

        amount = float(data["amount"])
        description = data.get("description", "Deposit")

        # Validate amount
        if amount <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Add funds using wallet method
        transaction = wallet.add_funds(amount, description)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Deposit completed successfully",
                    "transaction": transaction.to_dict(),
                    "new_balance": float(wallet.balance),
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid amount: {str(e)}"}), 400
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


@api_v1_bp.route("/wallets/withdraw", methods=["POST"])
@jwt_required()
def withdraw_funds():
    """Remove funds from wallet"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Validate required fields
        if "amount" not in data:
            return jsonify({"success": False, "message": "amount is required"}), 400

        amount = float(data["amount"])
        description = data.get("description", "Withdrawal")

        # Validate amount
        if amount <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Check if wallet has sufficient balance
        if not wallet.can_afford(amount):
            return jsonify({"success": False, "message": "Insufficient funds"}), 400

        # Deduct funds using wallet method
        transaction = wallet.deduct_funds(amount, description)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Withdrawal completed successfully",
                    "transaction": transaction.to_dict(),
                    "new_balance": float(wallet.balance),
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": f"Invalid amount: {str(e)}"}), 400
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
