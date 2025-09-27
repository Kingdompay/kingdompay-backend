"""
Test configuration and fixtures for KingdomPay tests
"""

import pytest
import os
import tempfile
from app import create_app
from extensions import db
from models import User, Wallet, Transaction, OTPVerification


@pytest.fixture
def app():
    """Create application for testing"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Set test configuration
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-bytes-long"

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret-key"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create test user"""
    with app.app_context():
        user = User(
            full_name="Test User",
            phone_number="+254712345678",
            email="test@example.com",
            is_phone_verified=True,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()

        # Create wallet for user
        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)
        db.session.commit()

        # Refresh the user to ensure it's properly bound to the session
        db.session.refresh(user)
        db.session.refresh(wallet)

        return user


@pytest.fixture
def test_wallet(app, test_user):
    """Create test wallet"""
    with app.app_context():
        wallet = Wallet.find_by_user_id(test_user.id)
        if wallet:
            db.session.refresh(wallet)
        return wallet


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    # Create a mock OTP verification
    with client.application.app_context():
        from services.auth_service import AuthService

        auth_service = AuthService()

        # Generate tokens directly for testing
        from flask_jwt_extended import create_access_token, create_refresh_token

        # Get the user ID directly without trying to refresh the object
        user_id = str(test_user.id)  # Convert to string for JWT

        access_token = create_access_token(identity=user_id)

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing"""
    return {
        "transaction_type": "DEPOSIT",
        "amount": 100.0,
        "description": "Test deposit",
        "status": "SUCCESS",
    }
