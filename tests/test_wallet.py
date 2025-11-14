"""
Test wallet functionality
"""

import pytest
import json


class TestWalletRoutes:
    """Test wallet routes"""

    def test_get_wallet_balance(self, client, auth_headers):
        """Test getting wallet balance"""
        response = client.get("/api/v1/wallets/balance", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "wallet" in data
        assert "balance" in data["wallet"]
        assert "currency" in data["wallet"]

    def test_get_wallet_balance_unauthorized(self, client):
        """Test getting wallet balance without authentication"""
        response = client.get("/api/v1/wallets/balance")

        assert response.status_code == 401

    def test_get_wallet_transactions(self, client, auth_headers):
        """Test getting wallet transactions"""
        response = client.get("/api/v1/wallets/transactions", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "transactions" in data
        assert "pagination" in data

    def test_get_wallet_transactions_with_pagination(self, client, auth_headers):
        """Test getting wallet transactions with pagination"""
        response = client.get(
            "/api/v1/wallets/transactions?page=1&per_page=10", headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 10

    def test_transfer_funds_success(self, client, auth_headers, app, test_user):
        """Test successful fund transfer via new /transfers with fees"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            # Create destination user and wallet
            dest_user = User(
                full_name="Destination User",
                phone_number="+254712345679",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(dest_user)
            db.session.flush()

            dest_wallet = Wallet(user_id=dest_user.id)
            db.session.add(dest_wallet)
            db.session.commit()

            # Add some funds to source wallet
            source_wallet = Wallet.find_by_user_id(test_user.id)
            source_wallet.balance = 1000.0
            db.session.commit()

            # Perform transfer using /transfers (fee-integrated)
            response = client.post(
                "/api/v1/transfers",
                headers={**auth_headers, "Idempotency-Key": "test-transfer-1"},
                json={
                    "to_wallet": dest_wallet.id,
                    "amount": 100.0,
                    "memo": "Test transfer",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "journal_id" in data
            assert "fee_breakdown" in data

            # No community involved → platform+federal fees (1.0% of 100 = 1)
            # Using Decimal math in service, but amounts are small: 100 + 1 = 101 total deduction
            # Refresh wallets and assert balances
            db.session.refresh(source_wallet)
            db.session.refresh(dest_wallet)

            assert float(source_wallet.balance) == pytest.approx(899.0, rel=1e-6)
            assert float(dest_wallet.balance) == pytest.approx(100.0, rel=1e-6)

    def test_transfer_funds_insufficient_balance(self, client, auth_headers, app):
        """Test transfer with insufficient balance"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            # Create destination user and wallet
            dest_user = User(
                full_name="Destination User",
                phone_number="+254712345680",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(dest_user)
            db.session.flush()

            dest_wallet = Wallet(user_id=dest_user.id)
            db.session.add(dest_wallet)
            db.session.commit()

            # Perform transfer with insufficient funds using /transfers
            response = client.post(
                "/api/v1/transfers",
                headers={**auth_headers, "Idempotency-Key": "test-transfer-2"},
                json={
                    "to_wallet": dest_wallet.id,
                    "amount": 10000.0,
                    "memo": "Test transfer",
                },
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Insufficient funds" in data["message"]

    def test_transfer_funds_invalid_destination(
        self, client, auth_headers, test_wallet, app
    ):
        """Test transfer to invalid destination wallet"""
        # First add some funds to the wallet so it passes the insufficient funds check
        with app.app_context():
            from extensions import db
            from models.wallet import Wallet

            # Query for the wallet again to get a fresh instance
            wallet = Wallet.query.get(test_wallet.id)
            wallet.balance = 1000.0
            db.session.commit()

        # Using /transfers with invalid wallet id
        response = client.post(
            "/api/v1/transfers",
            headers={**auth_headers, "Idempotency-Key": "test-transfer-3"},
            json={
                "to_wallet": 999999,
                "amount": 100.0,
                "memo": "Test transfer",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Wallet not found" in data["message"]

    def test_transfer_funds_self_transfer(self, client, auth_headers, test_wallet, app):
        """Test transfer to same wallet"""
        # First add some funds to the wallet so it passes the insufficient funds check
        with app.app_context():
            from extensions import db
            from models.wallet import Wallet

            # Query for the wallet again to get a fresh instance
            wallet = Wallet.query.get(test_wallet.id)
            wallet.balance = 1000.0
            db.session.commit()

        response = client.post(
            "/api/v1/transfers",
            headers={**auth_headers, "Idempotency-Key": "test-transfer-4"},
            json={
                "to_wallet": test_wallet.id,
                "amount": 100.0,
                "memo": "Self transfer",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Cannot transfer to the same wallet" in data["message"]

    def test_deposit_funds(self, client, auth_headers):
        """Test depositing funds"""
        response = client.post(
            "/api/v1/wallets/deposit",
            headers=auth_headers,
            json={"amount": 500.0, "description": "Test deposit"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "transaction" in data
        assert "new_balance" in data

    def test_deposit_funds_invalid_amount(self, client, auth_headers):
        """Test deposit with invalid amount"""
        response = client.post(
            "/api/v1/wallets/deposit",
            headers=auth_headers,
            json={"amount": -100.0, "description": "Invalid deposit"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Amount must be greater than 0" in data["message"]

    def test_withdraw_funds(self, client, auth_headers, app):
        """Test withdrawing funds"""
        # Add funds first
        with app.app_context():
            from models import Wallet
            from extensions import db

            wallet = Wallet.find_by_user_id(1)
            wallet.balance = 1000.0
            db.session.commit()

        response = client.post(
            "/api/v1/wallets/withdraw",
            headers=auth_headers,
            json={"amount": 200.0, "description": "Test withdrawal"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "transaction" in data
        assert data["new_balance"] == 800.0

    def test_withdraw_funds_insufficient_balance(self, client, auth_headers):
        """Test withdrawal with insufficient balance"""
        response = client.post(
            "/api/v1/wallets/withdraw",
            headers=auth_headers,
            json={"amount": 10000.0, "description": "Large withdrawal"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Insufficient funds" in data["message"]


class TestWalletModel:
    """Test wallet model"""

    def test_wallet_creation(self, app):
        """Test wallet creation"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345681",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            assert wallet.id is not None
            assert wallet.user_id == user.id
            assert wallet.balance == 0.0
            assert wallet.currency == "KES"
            assert wallet.display_number is not None
            assert wallet.display_number.startswith("WAL-")

    def test_wallet_can_afford(self, app):
        """Test wallet can_afford method"""
        with app.app_context():
            from models import Wallet
            from extensions import db

            wallet = Wallet(balance=100.0)

            assert wallet.can_afford(50.0) is True
            assert wallet.can_afford(100.0) is True
            assert wallet.can_afford(150.0) is False

    def test_wallet_add_funds(self, app):
        """Test wallet add_funds method"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345682",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id, balance=100.0)
            db.session.add(wallet)
            db.session.commit()

            transaction = wallet.add_funds(50.0, "Test deposit")

            assert transaction is not None
            assert transaction.transaction_type == "DEPOSIT"
            assert transaction.amount == 50.0
            assert wallet.balance == 150.0

    def test_wallet_deduct_funds(self, app):
        """Test wallet deduct_funds method"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345683",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id, balance=100.0)
            db.session.add(wallet)
            db.session.commit()

            transaction = wallet.deduct_funds(30.0, "Test withdrawal")

            assert transaction is not None
            assert transaction.transaction_type == "WITHDRAWAL"
            assert transaction.amount == 30.0
            assert wallet.balance == 70.0

    def test_wallet_deduct_funds_insufficient(self, app):
        """Test wallet deduct_funds with insufficient balance"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345684",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id, balance=50.0)
            db.session.add(wallet)
            db.session.commit()

            with pytest.raises(ValueError, match="Insufficient funds"):
                wallet.deduct_funds(100.0, "Large withdrawal")
