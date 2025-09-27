"""
Test script for KingdomPay authentication
Run this to test the authentication flow
"""

import requests
import json
import os

# Base URL for your API (override with TEST_BASE_URL env)
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:5000/api/v1")


def test_otp_flow():
    """Test the complete OTP authentication flow"""

    # Test phone number
    test_phone = "+254700000000"  # Replace with your phone number

    print("🧪 Testing KingdomPay Authentication Flow")
    print("=" * 50)

    # Step 1: Request OTP
    print(f"1. Requesting OTP for {test_phone}...")

    otp_response = requests.post(
        f"{BASE_URL}/auth/otp/request", json={"phone_number": test_phone}
    )

    print(f"   Status: {otp_response.status_code}")
    # Some environments might return non-JSON error bodies; guard decode
    try:
        print(f"   Response: {otp_response.json()}")
    except Exception:
        print("   Response: <non-json>")

    if otp_response.status_code != 200:
        print("❌ OTP request failed")
        return

    print("✅ OTP request successful")

    # Step 2: Verify OTP (non-interactive: use OTP_CODE if provided, else skip)
    print("\n2. Verifying OTP...")
    print("   Check your phone for the OTP code")

    otp_code_env = os.environ.get("OTP_CODE")
    if not otp_code_env:
        print(
            "   No OTP_CODE provided; skipping verification step in non-interactive run"
        )
        return

    verify_response = requests.post(
        f"{BASE_URL}/auth/otp/verify",
        json={
            "phone_number": test_phone,
            "otp_code": otp_code_env,
            "full_name": "Test User",
        },
    )

    print(f"   Status: {verify_response.status_code}")
    try:
        print(f"   Response: {verify_response.json()}")
    except Exception:
        print("   Response: <non-json>")

    if verify_response.status_code != 200:
        print("❌ OTP verification failed")
        return

    print("✅ OTP verification successful")

    # Extract tokens
    auth_data = verify_response.json()
    access_token = auth_data["tokens"]["access_token"]
    refresh_token = auth_data["tokens"]["refresh_token"]

    print(f"\n🔑 Access Token: {access_token[:50]}...")
    print(f"🔄 Refresh Token: {refresh_token[:50]}...")

    # Step 3: Test protected endpoint
    print("\n3. Testing protected endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}

    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"   Status: {me_response.status_code}")
    try:
        print(f"   Response: {me_response.json()}")
    except Exception:
        print("   Response: <non-json>")

    if me_response.status_code == 200:
        print("✅ Protected endpoint access successful")
    else:
        print("❌ Protected endpoint access failed")

    # Step 4: Test wallet balance
    print("\n4. Testing wallet balance...")
    wallet_response = requests.get(f"{BASE_URL}/wallets/balance", headers=headers)
    print(f"   Status: {wallet_response.status_code}")
    try:
        print(f"   Response: {wallet_response.json()}")
    except Exception:
        print("   Response: <non-json>")

    if wallet_response.status_code == 200:
        print("✅ Wallet balance access successful")
    else:
        print("❌ Wallet balance access failed")

    print("\n🎉 Authentication flow test completed!")


def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    base_no_version = BASE_URL.replace("/api/v1", "")
    response = requests.get(f"{base_no_version}/health")
    print(f"   Status: {response.status_code}")
    try:
        print(f"   Response: {response.json()}")
    except Exception:
        print("   Response: <non-json>")


if __name__ == "__main__":
    # Test health first
    test_health()
    print()

    # Test authentication flow
    test_otp_flow()
