"""
Ledger Service for KingdomPay
Handles transaction ledger operations
"""

from datetime import datetime
from extensions import db
from models.transaction import Transaction
from models.wallet import Wallet


class LedgerService:
    """Service for managing transaction ledger"""

    def __init__(self):
        self.initialized = True

    def create_transaction(self, transaction_data):
        """Create a new transaction in the ledger"""
        try:
            # Validate transaction data
            if not self.validate_transaction(transaction_data):
                return {"status": "failed", "message": "Invalid transaction data"}

            # Create transaction
            transaction = Transaction(
                source_wallet_id=transaction_data.get("source_wallet_id"),
                destination_wallet_id=transaction_data.get("destination_wallet_id"),
                transaction_type=transaction_data["transaction_type"],
                amount=transaction_data["amount"],
                source_balance_after=transaction_data.get("source_balance_after"),
                destination_balance_after=transaction_data.get(
                    "destination_balance_after"
                ),
                description=transaction_data.get("description", ""),
                status=transaction_data.get("status", "SUCCESS"),
            )

            db.session.add(transaction)
            db.session.commit()

            return {
                "status": "success",
                "message": "Transaction created successfully",
                "transaction_id": transaction.id,
                "reference_number": transaction.reference_number,
            }
        except Exception as e:
            db.session.rollback()
            return {
                "status": "failed",
                "message": f"Transaction creation failed: {str(e)}",
            }

    def get_transaction_history(self, user_id, limit=50, offset=0):
        """Get transaction history for a user"""
        try:
            transactions = Transaction.get_user_transactions(
                user_id, limit=limit, offset=offset
            )
            return {
                "status": "success",
                "transactions": [tx.to_dict() for tx in transactions],
                "count": len(transactions),
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Failed to retrieve transaction history: {str(e)}",
            }

    def validate_transaction(self, transaction_data):
        """Validate transaction data"""
        try:
            # Check required fields
            required_fields = ["transaction_type", "amount"]
            for field in required_fields:
                if field not in transaction_data:
                    return False

            # Validate transaction type
            valid_types = ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "FEE", "REFUND"]
            if transaction_data["transaction_type"] not in valid_types:
                return False

            # Validate amount
            amount = float(transaction_data["amount"])
            if amount <= 0:
                return False

            # Validate wallet IDs exist
            if transaction_data.get("source_wallet_id"):
                source_wallet = Wallet.query.get(transaction_data["source_wallet_id"])
                if not source_wallet:
                    return False

            if transaction_data.get("destination_wallet_id"):
                destination_wallet = Wallet.query.get(
                    transaction_data["destination_wallet_id"]
                )
                if not destination_wallet:
                    return False

            return True
        except (ValueError, TypeError):
            return False

    def get_wallet_balance(self, wallet_id):
        """Get wallet balance"""
        try:
            wallet = Wallet.query.get(wallet_id)
            if not wallet:
                return {"status": "failed", "message": "Wallet not found"}

            return {
                "status": "success",
                "wallet_id": wallet.id,
                "balance": float(wallet.balance),
                "currency": wallet.currency,
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Failed to get wallet balance: {str(e)}",
            }

    def get_transaction_by_reference(self, reference_number):
        """Get transaction by reference number"""
        try:
            transaction = Transaction.query.filter_by(
                reference_number=reference_number
            ).first()
            if not transaction:
                return {"status": "failed", "message": "Transaction not found"}

            return {
                "status": "success",
                "transaction": transaction.to_dict(),
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Failed to get transaction: {str(e)}",
            }

    def update_transaction_status(self, transaction_id, status):
        """Update transaction status"""
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return {"status": "failed", "message": "Transaction not found"}

            valid_statuses = ["SUCCESS", "PENDING", "FAILED", "CANCELLED"]
            if status not in valid_statuses:
                return {"status": "failed", "message": "Invalid status"}

            transaction.status = status
            db.session.commit()

            return {
                "status": "success",
                "message": "Transaction status updated successfully",
                "transaction": transaction.to_dict(),
            }
        except Exception as e:
            db.session.rollback()
            return {
                "status": "failed",
                "message": f"Failed to update transaction status: {str(e)}",
            }
