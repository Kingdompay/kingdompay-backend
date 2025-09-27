"""
Test database models
"""

import pytest
from datetime import datetime


class TestUserModel:
    """Test User model"""

    def test_user_creation(self, app):
        """Test user creation"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345689",
                email="test@example.com",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.full_name == "Test User"
            assert user.phone_number == "+254712345689"
            assert user.email == "test@example.com"
            assert user.is_phone_verified is True
            assert user.is_active is True

    def test_user_to_dict(self, app):
        """Test user to_dict method"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345690",
                email="test@example.com",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            user_dict = user.to_dict()

            assert user_dict["id"] == user.id
            assert user_dict["full_name"] == "Test User"
            assert user_dict["phone_number"] == "+254712345690"
            assert user_dict["email"] == "test@example.com"
            assert user_dict["is_phone_verified"] is True
            assert user_dict["is_active"] is True

    def test_user_find_by_phone(self, app):
        """Test finding user by phone number"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345691",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            found_user = User.find_by_phone("+254712345691")
            assert found_user is not None
            assert found_user.id == user.id

            # Test non-existent phone
            not_found = User.find_by_phone("+254712345692")
            assert not_found is None

    def test_user_find_by_email(self, app):
        """Test finding user by email"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345693",
                email="test@example.com",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            found_user = User.find_by_email("test@example.com")
            assert found_user is not None
            assert found_user.id == user.id

            # Test non-existent email
            not_found = User.find_by_email("notfound@example.com")
            assert not_found is None

    def test_user_password_methods(self, app):
        """Test user password methods"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345694",
                is_phone_verified=True,
                is_active=True,
            )

            # Test setting password
            user.set_password("testpassword")
            assert user.password is not None

            # Test checking password
            assert user.check_password("testpassword") is True
            assert user.check_password("wrongpassword") is False

            # Test checking password when no password is set
            user.password = None
            assert user.check_password("anypassword") is False

    def test_user_update_last_login(self, app):
        """Test updating last login"""
        with app.app_context():
            from models import User
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345695",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            initial_login = user.last_login
            user.update_last_login()

            assert user.last_login is not None
            assert user.last_login != initial_login


class TestWalletModel:
    """Test Wallet model"""

    def test_wallet_creation(self, app):
        """Test wallet creation"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345696",
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

    def test_wallet_to_dict(self, app):
        """Test wallet to_dict method"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345697",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id, balance=100.0)
            db.session.add(wallet)
            db.session.commit()

            wallet_dict = wallet.to_dict()

            assert wallet_dict["id"] == wallet.id
            assert wallet_dict["user_id"] == user.id
            assert wallet_dict["balance"] == 100.0
            assert wallet_dict["currency"] == "KES"
            assert wallet_dict["display_number"] == wallet.display_number

    def test_wallet_find_by_user_id(self, app):
        """Test finding wallet by user ID"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345698",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            found_wallet = Wallet.find_by_user_id(user.id)
            assert found_wallet is not None
            assert found_wallet.id == wallet.id

            # Test non-existent user
            not_found = Wallet.find_by_user_id(99999)
            assert not_found is None

    def test_wallet_find_by_display_number(self, app):
        """Test finding wallet by display number"""
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            user = User(
                full_name="Test User",
                phone_number="+254712345699",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            wallet = Wallet(user_id=user.id)
            db.session.add(wallet)
            db.session.commit()

            found_wallet = Wallet.find_by_display_number(wallet.display_number)
            assert found_wallet is not None
            assert found_wallet.id == wallet.id

            # Test non-existent display number
            not_found = Wallet.find_by_display_number("INVALID-WALLET")
            assert not_found is None


class TestTransactionModel:
    """Test Transaction model"""

    def test_transaction_creation(self, app):
        """Test transaction creation"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create users and wallets
            user1 = User(
                full_name="Source User",
                phone_number="+254712345700",
                is_phone_verified=True,
                is_active=True,
            )
            user2 = User(
                full_name="Destination User",
                phone_number="+254712345701",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add_all([user1, user2])
            db.session.flush()

            wallet1 = Wallet(user_id=user1.id)
            wallet2 = Wallet(user_id=user2.id)
            db.session.add_all([wallet1, wallet2])
            db.session.commit()

            transaction = Transaction(
                source_wallet_id=wallet1.id,
                destination_wallet_id=wallet2.id,
                transaction_type="TRANSFER",
                amount=100.0,
                source_balance_after=900.0,
                destination_balance_after=100.0,
                description="Test transfer",
                status="SUCCESS",
            )
            db.session.add(transaction)
            db.session.commit()

            assert transaction.id is not None
            assert transaction.source_wallet_id == wallet1.id
            assert transaction.destination_wallet_id == wallet2.id
            assert transaction.transaction_type == "TRANSFER"
            assert transaction.amount == 100.0
            assert transaction.reference_number is not None
            assert transaction.status == "SUCCESS"

    def test_transaction_to_dict(self, app):
        """Test transaction to_dict method"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create users and wallets
            user1 = User(
                full_name="Source User",
                phone_number="+254712345702",
                is_phone_verified=True,
                is_active=True,
            )
            user2 = User(
                full_name="Destination User",
                phone_number="+254712345703",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add_all([user1, user2])
            db.session.flush()

            wallet1 = Wallet(user_id=user1.id)
            wallet2 = Wallet(user_id=user2.id)
            db.session.add_all([wallet1, wallet2])
            db.session.commit()

            transaction = Transaction(
                source_wallet_id=wallet1.id,
                destination_wallet_id=wallet2.id,
                transaction_type="TRANSFER",
                amount=100.0,
                source_balance_after=900.0,
                destination_balance_after=100.0,
                description="Test transfer",
                status="SUCCESS",
            )
            db.session.add(transaction)
            db.session.commit()

            transaction_dict = transaction.to_dict()

            assert transaction_dict["id"] == transaction.id
            assert transaction_dict["source_wallet_id"] == wallet1.id
            assert transaction_dict["destination_wallet_id"] == wallet2.id
            assert transaction_dict["transaction_type"] == "TRANSFER"
            assert transaction_dict["amount"] == 100.0
            assert transaction_dict["reference_number"] == transaction.reference_number
            assert transaction_dict["status"] == "SUCCESS"

    def test_transaction_get_user_transactions(self, app):
        """Test getting user transactions"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create users and wallets
            user1 = User(
                full_name="User 1",
                phone_number="+254712345704",
                is_phone_verified=True,
                is_active=True,
            )
            user2 = User(
                full_name="User 2",
                phone_number="+254712345705",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add_all([user1, user2])
            db.session.flush()

            wallet1 = Wallet(user_id=user1.id)
            wallet2 = Wallet(user_id=user2.id)
            db.session.add_all([wallet1, wallet2])
            db.session.commit()

            # Create transactions
            transaction1 = Transaction(
                source_wallet_id=wallet1.id,
                destination_wallet_id=wallet2.id,
                transaction_type="TRANSFER",
                amount=100.0,
                description="Transfer from user1 to user2",
                status="SUCCESS",
            )
            transaction2 = Transaction(
                source_wallet_id=wallet2.id,
                destination_wallet_id=wallet1.id,
                transaction_type="TRANSFER",
                amount=50.0,
                description="Transfer from user2 to user1",
                status="SUCCESS",
            )
            db.session.add_all([transaction1, transaction2])
            db.session.commit()

            # Get transactions for user1
            user1_transactions = Transaction.get_user_transactions(user1.id)
            assert len(user1_transactions) == 2

            # Get transactions for user2
            user2_transactions = Transaction.get_user_transactions(user2.id)
            assert len(user2_transactions) == 2

    def test_transaction_get_wallet_transactions(self, app):
        """Test getting wallet transactions"""
        with app.app_context():
            from models import User, Wallet, Transaction
            from extensions import db

            # Create users and wallets
            user1 = User(
                full_name="User 1",
                phone_number="+254712345706",
                is_phone_verified=True,
                is_active=True,
            )
            user2 = User(
                full_name="User 2",
                phone_number="+254712345707",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add_all([user1, user2])
            db.session.flush()

            wallet1 = Wallet(user_id=user1.id)
            wallet2 = Wallet(user_id=user2.id)
            db.session.add_all([wallet1, wallet2])
            db.session.commit()

            # Create transactions
            transaction1 = Transaction(
                source_wallet_id=wallet1.id,
                destination_wallet_id=wallet2.id,
                transaction_type="TRANSFER",
                amount=100.0,
                description="Transfer from wallet1 to wallet2",
                status="SUCCESS",
            )
            transaction2 = Transaction(
                source_wallet_id=wallet2.id,
                destination_wallet_id=wallet1.id,
                transaction_type="TRANSFER",
                amount=50.0,
                description="Transfer from wallet2 to wallet1",
                status="SUCCESS",
            )
            db.session.add_all([transaction1, transaction2])
            db.session.commit()

            # Get transactions for wallet1
            wallet1_transactions = Transaction.get_wallet_transactions(wallet1.id)
            assert len(wallet1_transactions) == 2

            # Get transactions for wallet2
            wallet2_transactions = Transaction.get_wallet_transactions(wallet2.id)
            assert len(wallet2_transactions) == 2


class TestOTPModel:
    """Test OTP model"""

    def test_otp_generation(self, app):
        """Test OTP generation"""
        with app.app_context():
            from models import OTPVerification

            phone_number = "+254712345708"
            otp = OTPVerification.generate_otp(phone_number)

            assert otp is not None
            assert otp.phone_number == phone_number
            assert otp.otp_hash is not None
            assert otp.expires_at is not None
            assert otp.is_used is False
            assert otp.attempts == 0
            assert hasattr(otp, "otp_code")
            assert len(otp.otp_code) == 6

    def test_otp_verification_success(self, app):
        """Test successful OTP verification"""
        with app.app_context():
            from models import OTPVerification

            phone_number = "+254712345709"
            otp = OTPVerification.generate_otp(phone_number)

            # Verify with correct code
            result = OTPVerification.verify_otp(phone_number, otp.otp_code)
            assert result is True

            # Check that OTP is marked as used
            assert otp.is_used is True

    def test_otp_verification_failure(self, app):
        """Test failed OTP verification"""
        with app.app_context():
            from models import OTPVerification

            phone_number = "+254712345710"
            otp = OTPVerification.generate_otp(phone_number)

            # Verify with incorrect code
            result = OTPVerification.verify_otp(phone_number, "000000")
            assert result is False

            # Check that attempts are incremented
            assert otp.attempts == 1

    def test_otp_cleanup_expired(self, app):
        """Test OTP cleanup"""
        with app.app_context():
            from models import OTPVerification
            from datetime import datetime, timedelta, timezone

            phone_number = "+254712345711"
            otp = OTPVerification.generate_otp(phone_number)

            # Manually set expiry to past
            otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            from extensions import db

            db.session.commit()

            # Cleanup expired OTPs
            cleaned_count = OTPVerification.cleanup_expired()
            assert cleaned_count == 1

    def test_otp_get_recent_attempts(self, app):
        """Test getting recent OTP attempts"""
        with app.app_context():
            from models import OTPVerification

            phone_number = "+254712345712"

            # Generate multiple OTPs
            OTPVerification.generate_otp(phone_number)
            OTPVerification.generate_otp(phone_number)

            # Get recent attempts
            attempts = OTPVerification.get_recent_attempts(phone_number)
            assert attempts >= 2
