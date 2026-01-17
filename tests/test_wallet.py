"""
Unit tests for wallet endpoints
"""

import pytest
from decimal import Decimal
from app import create_app
from extensions import db
from models.user import User
from models.wallet import Wallet


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get auth headers for authenticated requests"""
    # Request and verify OTP
    otp_response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": "+254712345678"}
    )
    otp_code = otp_response.get_json()["otp_code"]
    
    verify_response = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "phone_number": "+254712345678",
            "otp_code": otp_code,
            "full_name": "Test User"
        }
    )
    token = verify_response.get_json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


class TestWalletEndpoints:
    """Test wallet endpoints"""

    def test_get_balance_unauthorized(self, client):
        """Test getting balance without auth"""
        response = client.get("/api/v1/wallets/balance")
        assert response.status_code == 401

    def test_get_balance_authorized(self, client, auth_headers):
        """Test getting balance with auth"""
        response = client.get(
            "/api/v1/wallets/balance",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "wallet" in data
        assert "balance" in data["wallet"]

    def test_get_transactions_empty(self, client, auth_headers):
        """Test getting transactions when none exist"""
        response = client.get(
            "/api/v1/wallets/transactions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["transactions"] == []

    def test_transfer_insufficient_balance(self, client, auth_headers):
        """Test transfer with insufficient balance"""
        response = client.post(
            "/api/v1/wallets/transfer",
            headers={
                **auth_headers,
                "Idempotency-Key": "test-transfer-1"
            },
            json={
                "recipient_phone": "+254700000001",
                "amount": 1000000
            }
        )
        # Should fail due to insufficient balance
        assert response.status_code in [400, 422]

    def test_transfer_missing_fields(self, client, auth_headers):
        """Test transfer with missing fields"""
        response = client.post(
            "/api/v1/wallets/transfer",
            headers={
                **auth_headers,
                "Idempotency-Key": "test-transfer-2"
            },
            json={}
        )
        assert response.status_code == 400


class TestCurrencyEndpoints:
    """Test currency endpoints"""

    def test_get_currencies(self, client):
        """Test getting supported currencies"""
        response = client.get("/api/v1/currencies")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "currencies" in data
        assert len(data["currencies"]) > 0
        
        # Check KES is in the list
        currency_codes = [c["code"] for c in data["currencies"]]
        assert "KES" in currency_codes
        assert "USD" in currency_codes

    def test_get_exchange_rates(self, client):
        """Test getting exchange rates"""
        response = client.get("/api/v1/currencies/rates")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "rates" in data
        assert data["base"] == "KES"

    def test_convert_currency(self, client, auth_headers):
        """Test currency conversion"""
        response = client.post(
            "/api/v1/currencies/convert",
            headers=auth_headers,
            json={
                "amount": 1000,
                "from_currency": "KES",
                "to_currency": "USD"
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "converted_amount" in data
        assert data["from_currency"] == "KES"
        assert data["to_currency"] == "USD"


class TestFeeEndpoints:
    """Test fee calculation endpoints"""

    def test_calculate_fees(self, client, auth_headers):
        """Test fee calculation"""
        response = client.post(
            "/api/v1/fees/calculate",
            headers=auth_headers,
            json={"amount": 1000}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "fees" in data

    def test_calculate_fees_negative_amount(self, client, auth_headers):
        """Test fee calculation with negative amount"""
        response = client.post(
            "/api/v1/fees/calculate",
            headers=auth_headers,
            json={"amount": -100}
        )
        assert response.status_code == 400

    def test_calculate_fees_exceeds_max(self, client, auth_headers):
        """Test fee calculation exceeding maximum"""
        response = client.post(
            "/api/v1/fees/calculate",
            headers=auth_headers,
            json={"amount": 100000000}  # 100 million
        )
        assert response.status_code == 400
