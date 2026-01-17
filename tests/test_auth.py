"""
Unit tests for authentication endpoints
"""

import pytest
from app import create_app
from extensions import db
from models.user import User


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


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    def test_request_otp_missing_phone(self, client):
        """Test OTP request without phone number"""
        response = client.post(
            "/api/v1/auth/otp/request",
            json={}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_request_otp_valid_phone(self, client):
        """Test OTP request with valid phone number"""
        response = client.post(
            "/api/v1/auth/otp/request",
            json={"phone_number": "+254712345678"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "otp_code" in data  # Development mode includes OTP

    def test_request_otp_local_format(self, client):
        """Test OTP request with 07 format"""
                response = client.post(
            "/api/v1/auth/otp/request",
            json={"phone_number": "0712345678"}
                )
                assert response.status_code == 200
        data = response.get_json()
                assert data["success"] is True
        assert data["phone_number"] == "+254712345678"

    def test_verify_otp_missing_fields(self, client):
        """Test OTP verification without required fields"""
        response = client.post(
            "/api/v1/auth/otp/verify",
            json={}
                )
        assert response.status_code == 400

    def test_verify_otp_invalid_code(self, client):
        """Test OTP verification with invalid code"""
        # First request OTP
        client.post(
            "/api/v1/auth/otp/request",
            json={"phone_number": "+254712345678"}
        )
        
        # Try with wrong code
        response = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone_number": "+254712345678",
                "otp_code": "000000",
                "full_name": "Test User"
            }
        )
        assert response.status_code == 400

    def test_full_auth_flow(self, client):
        """Test complete authentication flow"""
        # Request OTP
        otp_response = client.post(
            "/api/v1/auth/otp/request",
            json={"phone_number": "+254712345678"}
        )
        assert otp_response.status_code == 200
        otp_code = otp_response.get_json()["otp_code"]
        
        # Verify OTP
        verify_response = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone_number": "+254712345678",
                "otp_code": otp_code,
                "full_name": "Test User"
            }
        )
        assert verify_response.status_code == 200
        data = verify_response.get_json()
        assert data["success"] is True
        assert "access_token" in data
        assert "refresh_token" in data

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_current_user_authorized(self, client):
        """Test getting current user with valid token"""
        # Get token
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
        
        # Get user info
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["phone_number"] == "+254712345678"
