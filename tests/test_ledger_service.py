"""
Test ledger service functionality
"""

import pytest
from services.ledger_service import LedgerService


class TestLedgerService:
    """Test ledger service"""

    def test_create_transaction_success(self, app, sample_transaction_data):
        """Test successful transaction creation"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            # Create test user and wallet
            user = User(
                full_name="Test User",
                phone_number="+254712345685",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            # Add wallet ID to transaction data
            sample_transaction_data["destination_wallet_id"] = wallet.id
            sample_transaction_data["destination_balance_after"] = 100.0

            ledger_service = LedgerService()
            result = ledger_service.create_transaction(sample_transaction_data)

            assert result["status"] == "success"
            assert "transaction_id" in result
            assert "reference_number" in result

    def test_create_transaction_invalid_data(self, app):
        """Test transaction creation with invalid data"""
        with app.app_context():
            ledger_service = LedgerService()
            invalid_data = {"transaction_type": "INVALID_TYPE", "amount": -100.0}

            result = ledger_service.create_transaction(invalid_data)

            assert result["status"] == "failed"
            assert "Invalid transaction data" in result["message"]

    def test_validate_transaction_valid(self, app):
        """Test transaction validation with valid data"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            # Create test user and wallet
            user = User(
                full_name="Test User",
                phone_number="+254712345686",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            ledger_service = LedgerService()
            valid_data = {
                "transaction_type": "DEPOSIT",
                "amount": 100.0,
                "destination_wallet_id": wallet.id,
            }

            assert ledger_service.validate_transaction(valid_data) is True

    def test_validate_transaction_invalid_type(self, app):
        """Test transaction validation with invalid type"""
        with app.app_context():
            ledger_service = LedgerService()
            invalid_data = {"transaction_type": "INVALID_TYPE", "amount": 100.0}

            assert ledger_service.validate_transaction(invalid_data) is False

    def test_validate_transaction_invalid_amount(self, app):
        """Test transaction validation with invalid amount"""
        with app.app_context():
            ledger_service = LedgerService()
            invalid_data = {"transaction_type": "DEPOSIT", "amount": -100.0}

            assert ledger_service.validate_transaction(invalid_data) is False

    def test_validate_transaction_missing_fields(self, app):
        """Test transaction validation with missing fields"""
        with app.app_context():
            ledger_service = LedgerService()
            invalid_data = {
                "amount": 100.0
                # Missing transaction_type
            }

            assert ledger_service.validate_transaction(invalid_data) is False

    def test_get_transaction_history(self, app, test_user):
        """Test getting transaction history"""
        with app.app_context():
            ledger_service = LedgerService()
            result = ledger_service.get_transaction_history(test_user.id)

            assert result["status"] == "success"
            assert "transactions" in result
            assert "count" in result

    def test_get_wallet_balance(self, app, test_wallet):
        """Test getting wallet balance"""
        with app.app_context():
            ledger_service = LedgerService()
            result = ledger_service.get_wallet_balance(test_wallet.id)

            assert result["status"] == "success"
            assert "wallet_id" in result
            assert "balance" in result
            assert "currency" in result

    def test_get_wallet_balance_not_found(self, app):
        """Test getting balance for non-existent wallet"""
        with app.app_context():
            ledger_service = LedgerService()
            result = ledger_service.get_wallet_balance(99999)

            assert result["status"] == "failed"
            assert "Wallet not found" in result["message"]

    def test_get_transaction_by_reference(self, app):
        """Test getting transaction by reference number"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create test user and wallet
            user = User(
                full_name="Test User",
                phone_number="+254712345687",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            # Create transaction
            transaction = Transaction(
                destination_wallet_id=wallet.id,
                transaction_type="DEPOSIT",
                amount=100.0,
                destination_balance_after=100.0,
                description="Test transaction",
                status="SUCCESS",
            )
            db.session.add(transaction)
            db.session.commit()

            ledger_service = LedgerService()
            result = ledger_service.get_transaction_by_reference(
                transaction.reference_number
            )

            assert result["status"] == "success"
            assert "transaction" in result
            assert (
                result["transaction"]["reference_number"]
                == transaction.reference_number
            )

    def test_get_transaction_by_reference_not_found(self, app):
        """Test getting transaction by non-existent reference"""
        with app.app_context():
            ledger_service = LedgerService()
            result = ledger_service.get_transaction_by_reference("INVALID-REF")

            assert result["status"] == "failed"
            assert "Transaction not found" in result["message"]

    def test_update_transaction_status(self, app):
        """Test updating transaction status"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create test user and wallet
            user = User(
                full_name="Test User",
                phone_number="+254712345688",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            # Create transaction
            transaction = Transaction(
                destination_wallet_id=wallet.id,
                transaction_type="DEPOSIT",
                amount=100.0,
                destination_balance_after=100.0,
                description="Test transaction",
                status="PENDING",
            )
            db.session.add(transaction)
            db.session.commit()

            ledger_service = LedgerService()
            result = ledger_service.update_transaction_status(transaction.id, "SUCCESS")

            assert result["status"] == "success"
            assert "transaction" in result
            assert result["transaction"]["status"] == "SUCCESS"

    def test_update_transaction_status_invalid(self, app, test_wallet):
        """Test updating transaction status with invalid status"""
        with app.app_context():
            ledger_service = LedgerService()

            # First create a transaction
            transaction_data = {
                "destination_wallet_id": test_wallet.id,
                "transaction_type": "DEPOSIT",
                "amount": 100.0,
                "destination_balance_after": 100.0,
                "description": "Test deposit",
                "status": "SUCCESS",
            }

            create_result = ledger_service.create_transaction(transaction_data)
            assert create_result["status"] == "success"
            transaction_id = create_result["transaction_id"]

            # Now try to update with invalid status
            result = ledger_service.update_transaction_status(
                transaction_id, "INVALID_STATUS"
            )

            assert result["status"] == "failed"
            assert "Invalid status" in result["message"]

    def test_update_transaction_status_not_found(self, app):
        """Test updating status for non-existent transaction"""
        with app.app_context():
            ledger_service = LedgerService()
            result = ledger_service.update_transaction_status(99999, "SUCCESS")

            assert result["status"] == "failed"
            assert "Transaction not found" in result["message"]
