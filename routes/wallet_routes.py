"""
Wallet routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from decimal import Decimal
from routes import api_v1_bp
from services.auth_service import AuthService
from services.ledger_service import LedgerService
from services.transfer_service import TransferService
from models.wallet import Wallet
from models.transaction import Transaction

auth_service = AuthService()
ledger_service = LedgerService()
transfer_service = TransferService()


@api_v1_bp.route("/wallets/balance", methods=["GET"])
@jwt_required()
def get_wallet_balance():
    """
    Get wallet balance
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    responses:
      200:
        description: Wallet balance retrieved
        schema:
          type: object
          properties:
            success:
              type: boolean
            wallet:
              type: object
              properties:
                id:
                  type: integer
                balance:
                  type: number
                currency:
                  type: string
      401:
        description: Unauthorized
      404:
        description: Wallet not found
    """
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
    """
    Get transaction history
    ---
    tags:
      - Wallet
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 20
    responses:
      200:
        description: Transaction list
      401:
        description: Unauthorized
    """
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
    """Get wallet ledger backed by transactions for now (cursor pagination placeholder)"""
    # Reuse current pagination params
    return get_wallet_transactions()


@api_v1_bp.route("/transfers", methods=["POST"])
@jwt_required()
def create_transfer():
    """Create wallet-to-wallet transfer with Idempotency-Key"""
    try:
        data = request.get_json() or {}
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return (
                jsonify(
                    {"success": False, "message": "Idempotency-Key header required"}
                ),
                400,
            )

        from_wallet = Wallet.find_by_user_id(user.id)
        if not from_wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        to_wallet_id = data.get("to_wallet") or data.get("to_wallet_id")
        amount = data.get("amount")
        currency = data.get("currency") or from_wallet.currency
        memo = data.get("memo")

        if not to_wallet_id or amount is None:
            return (
                jsonify(
                    {"success": False, "message": "to_wallet and amount are required"}
                ),
                400,
            )

        # Use TransferService for fee-integrated transfers
        result = transfer_service.process_transfer(
            from_wallet_id=from_wallet.id,
            to_wallet_id=int(to_wallet_id),
            amount=Decimal(str(amount)),
            currency=currency,
            memo=memo,
            idempotency_key=idem_key,
            user_id=user.id,
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/wallets/transfer", methods=["POST"])
@jwt_required()
def transfer_funds():
    """Transfer funds between wallets
    
    Requires either:
    - X-CSRF-Token header (for browser/web clients)
    - Idempotency-Key header (for API clients)
    """
    try:
        # Check for either CSRF token or Idempotency-Key
        csrf_token = request.headers.get("X-CSRF-Token")
        idempotency_key = request.headers.get("Idempotency-Key")
        
        if not csrf_token and not idempotency_key:
            return jsonify({
                "success": False,
                "message": "Either X-CSRF-Token or Idempotency-Key header is required",
                "code": "MISSING_SECURITY_TOKEN"
            }), 400
        
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        source_wallet = Wallet.find_by_user_id(user.id)
        if not source_wallet:
            return (
                jsonify({"success": False, "message": "Source wallet not found"}),
                404,
            )

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Validate required fields - accept multiple field names for flexibility
        dest_wallet = data.get("destination_wallet_number") or data.get("destination_wallet_id") or data.get("to_wallet_id")
        amount = data.get("amount")
        description = data.get("description") or data.get("memo", "Transfer")
        
        if not dest_wallet:
            return jsonify({"success": False, "message": "destination_wallet_number or destination_wallet_id is required"}), 400
        if not amount:
            return jsonify({"success": False, "message": "amount is required"}), 400

        # Convert amount to Decimal for consistent arithmetic
        try:
            amount_decimal = Decimal(str(amount))
        except (ValueError, TypeError):
            return (
                jsonify({"success": False, "message": "Invalid amount format"}),
                400,
            )

        # Validate amount
        if amount_decimal <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Check if source wallet has sufficient balance
        if not source_wallet.can_afford(amount_decimal):
            return jsonify({"success": False, "message": "Insufficient funds"}), 400

        # Find destination wallet - try by display number first, then by ID
        destination_wallet = None
        if isinstance(dest_wallet, str) and dest_wallet.startswith("WAL-"):
            destination_wallet = Wallet.find_by_display_number(dest_wallet)
        elif isinstance(dest_wallet, int) or (isinstance(dest_wallet, str) and dest_wallet.isdigit()):
            destination_wallet = Wallet.query.get(int(dest_wallet))
        else:
            destination_wallet = Wallet.find_by_display_number(dest_wallet)
            
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
    """Add funds to wallet (admin/system operation)
    
    Requires either X-CSRF-Token or Idempotency-Key header
    """
    try:
        # Check for security token
        csrf_token = request.headers.get("X-CSRF-Token")
        idempotency_key = request.headers.get("Idempotency-Key")
        
        if not csrf_token and not idempotency_key:
            return jsonify({
                "success": False,
                "message": "Either X-CSRF-Token or Idempotency-Key header is required",
                "code": "MISSING_SECURITY_TOKEN"
            }), 400
        
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        wallet = Wallet.find_by_user_id(user.id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Validate required fields
        if "amount" not in data:
            return jsonify({"success": False, "message": "amount is required"}), 400

        amount = data["amount"]
        description = data.get("description", "Deposit")

        # Convert amount to Decimal for consistent arithmetic
        from decimal import Decimal

        try:
            amount_decimal = Decimal(str(amount))
        except (ValueError, TypeError):
            return (
                jsonify({"success": False, "message": "Invalid amount format"}),
                400,
            )

        # Validate amount
        if amount_decimal <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Add funds using wallet method
        transaction = wallet.add_funds(amount_decimal, description)

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
    """Remove funds from wallet
    
    Requires either X-CSRF-Token or Idempotency-Key header
    """
    try:
        # Check for security token
        csrf_token = request.headers.get("X-CSRF-Token")
        idempotency_key = request.headers.get("Idempotency-Key")
        
        if not csrf_token and not idempotency_key:
            return jsonify({
                "success": False,
                "message": "Either X-CSRF-Token or Idempotency-Key header is required",
                "code": "MISSING_SECURITY_TOKEN"
            }), 400
        
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

        amount = data["amount"]
        description = data.get("description", "Withdrawal")

        # Convert amount to Decimal for consistent arithmetic
        from decimal import Decimal

        try:
            amount_decimal = Decimal(str(amount))
        except (ValueError, TypeError):
            return (
                jsonify({"success": False, "message": "Invalid amount format"}),
                400,
            )

        # Validate amount
        if amount_decimal <= 0:
            return (
                jsonify({"success": False, "message": "Amount must be greater than 0"}),
                400,
            )

        # Check if wallet has sufficient balance
        if not wallet.can_afford(amount_decimal):
            return jsonify({"success": False, "message": "Insufficient funds"}), 400

        # Deduct funds using wallet method
        transaction = wallet.deduct_funds(amount_decimal, description)

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
