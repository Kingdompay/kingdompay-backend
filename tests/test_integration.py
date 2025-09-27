"""
Integration tests for KingdomPay API
"""

import pytest
import json


class TestAPIIntegration:
    """Test complete API workflows"""

    def test_complete_user_registration_flow(self, client, app):
        """Test complete user registration and wallet creation flow"""
        phone_number = "+254712345800"

        # Step 1: Request OTP
        response = client.post(
            "/api/v1/auth/otp/request", json={"phone_number": phone_number}
        )
        assert response.status_code == 200

        # Step 2: Get OTP from database and verify
        with app.app_context():
            from models.otp import OTPVerification

            otp_record = OTPVerification.query.filter_by(
                phone_number=phone_number, is_used=False
            ).first()

            if otp_record:
                # For testing, we'll use a known OTP code
                otp_code = "123456"

                # Update the OTP record to use this test code
                from werkzeug.security import generate_password_hash
                from extensions import db

                otp_record.otp_hash = generate_password_hash(otp_code)
                db.session.commit()

                # Step 3: Verify OTP and create user
                response = client.post(
                    "/api/v1/auth/otp/verify",
                    json={
                        "phone_number": phone_number,
                        "otp_code": otp_code,
                        "full_name": "Integration Test User",
                    },
                )
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert "tokens" in data
                assert "user" in data

                access_token = data["tokens"]["access_token"]
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                # Step 4: Check that wallet was created
                response = client.get("/api/v1/wallets/balance", headers=headers)
                assert response.status_code == 200
                wallet_data = json.loads(response.data)
                assert wallet_data["success"] is True
                assert "wallet" in wallet_data
                assert wallet_data["wallet"]["balance"] == 0.0

    def test_complete_transfer_workflow(self, client, auth_headers, app):
        """Test complete transfer workflow between two users"""
        # Create second user and wallet
        with app.app_context():
            from models import User, Wallet
            from extensions import db

            # Create destination user
            dest_user = User(
                full_name="Destination User",
                phone_number="+254712345801",
                is_phone_verified=True,
                is_active=True,
            )
            db.session.add(dest_user)
            db.session.flush()

            dest_wallet = Wallet(user_id=dest_user.id)
            db.session.add(dest_wallet)

            # Add funds to source wallet
            source_wallet = Wallet.find_by_user_id(1)  # Assuming test_user has id 1
            source_wallet.balance = 1000.0
            db.session.commit()

            # Step 1: Check initial balances
            response = client.get("/api/v1/wallets/balance", headers=auth_headers)
            assert response.status_code == 200
            initial_data = json.loads(response.data)
            initial_balance = initial_data["wallet"]["balance"]

            # Step 2: Perform transfer
            response = client.post(
                "/api/v1/wallets/transfer",
                headers=auth_headers,
                json={
                    "destination_wallet_number": dest_wallet.display_number,
                    "amount": 200.0,
                    "description": "Integration test transfer",
                },
            )
            assert response.status_code == 200
            transfer_data = json.loads(response.data)
            assert transfer_data["success"] is True
            assert transfer_data["source_balance"] == 800.0
            assert transfer_data["destination_balance"] == 200.0

            # Step 3: Verify transaction was recorded
            response = client.get("/api/v1/wallets/transactions", headers=auth_headers)
            assert response.status_code == 200
            transactions_data = json.loads(response.data)
            assert transactions_data["success"] is True
            assert len(transactions_data["transactions"]) > 0

            # Find the transfer transaction
            transfer_transaction = None
            for tx in transactions_data["transactions"]:
                if tx["transaction_type"] == "TRANSFER" and tx["amount"] == 200.0:
                    transfer_transaction = tx
                    break

            assert transfer_transaction is not None
            assert transfer_transaction["status"] == "SUCCESS"

    def test_deposit_and_withdrawal_workflow(self, client, auth_headers, app):
        """Test deposit and withdrawal workflow"""
        # Step 1: Deposit funds
        response = client.post(
            "/api/v1/wallets/deposit",
            headers=auth_headers,
            json={"amount": 500.0, "description": "Integration test deposit"},
        )
        assert response.status_code == 200
        deposit_data = json.loads(response.data)
        assert deposit_data["success"] is True
        assert deposit_data["new_balance"] == 500.0

        # Step 2: Withdraw funds
        response = client.post(
            "/api/v1/wallets/withdraw",
            headers=auth_headers,
            json={"amount": 150.0, "description": "Integration test withdrawal"},
        )
        assert response.status_code == 200
        withdrawal_data = json.loads(response.data)
        assert withdrawal_data["success"] is True
        assert withdrawal_data["new_balance"] == 350.0

        # Step 3: Verify final balance
        response = client.get("/api/v1/wallets/balance", headers=auth_headers)
        assert response.status_code == 200
        balance_data = json.loads(response.data)
        assert balance_data["wallet"]["balance"] == 350.0

    def test_error_handling_workflow(self, client, auth_headers):
        """Test error handling in various scenarios"""
        # Test 1: Transfer with insufficient funds
        response = client.post(
            "/api/v1/wallets/transfer",
            headers=auth_headers,
            json={
                "destination_wallet_number": "WAL-999999999",
                "amount": 10000.0,
                "description": "Large transfer",
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

        # Test 2: Withdrawal with insufficient funds
        response = client.post(
            "/api/v1/wallets/withdraw",
            headers=auth_headers,
            json={"amount": 10000.0, "description": "Large withdrawal"},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

        # Test 3: Invalid amount
        response = client.post(
            "/api/v1/wallets/deposit",
            headers=auth_headers,
            json={"amount": -100.0, "description": "Invalid deposit"},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    def test_rate_limiting(self, client):
        """Test rate limiting on OTP requests"""
        phone_number = "+254712345802"

        # Make multiple OTP requests quickly
        for i in range(6):  # Should hit the 5 per minute limit
            response = client.post(
                "/api/v1/auth/otp/request", json={"phone_number": phone_number}
            )

            if i < 5:
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429

    def test_profile_update_workflow(self, client, auth_headers):
        """Test complete profile update workflow"""
        # Step 1: Get current profile
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        initial_data = json.loads(response.data)
        initial_name = initial_data["user"]["full_name"]

        # Step 2: Update profile
        response = client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={
                "full_name": "Updated Integration User",
                "email": "integration@example.com",
            },
        )
        assert response.status_code == 200
        update_data = json.loads(response.data)
        assert update_data["success"] is True
        assert update_data["user"]["full_name"] == "Updated Integration User"
        assert update_data["user"]["email"] == "integration@example.com"

        # Step 3: Verify changes persisted
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        final_data = json.loads(response.data)
        assert final_data["user"]["full_name"] == "Updated Integration User"
        assert final_data["user"]["email"] == "integration@example.com"

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "kingdompay-api"
        assert data["version"] == "1.0.0"

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints"""
        protected_endpoints = [
            ("/api/v1/auth/me", "GET"),
            ("/api/v1/wallets/balance", "GET"),
            ("/api/v1/wallets/transactions", "GET"),
            ("/api/v1/wallets/deposit", "POST"),
            ("/api/v1/wallets/withdraw", "POST"),
            ("/api/v1/wallets/transfer", "POST"),
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})

            assert response.status_code == 401

    def test_invalid_json_handling(self, client, auth_headers):
        """Test handling of invalid JSON requests"""
        # Test with invalid JSON
        response = client.post(
            "/api/v1/wallets/deposit", headers=auth_headers, data="invalid json"
        )
        assert response.status_code == 400

        # Test with missing required fields
        response = client.post(
            "/api/v1/wallets/transfer", headers=auth_headers, json={}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
