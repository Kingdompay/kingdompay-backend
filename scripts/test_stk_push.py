#!/usr/bin/env python3
"""
Test script for M-Pesa STK Push
Tests the /api/v1/mpesa/pay endpoint
"""

import os
import sys
import requests
import json
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

def print_step(step_num, message):
    """Print formatted step message"""
    print(f"\n{'='*50}")
    print(f"Step {step_num}: {message}")
    print(f"{'='*50}")

def test_stk_push():
    """Test STK Push payment"""
    print("\n" + "="*60)
    print("🧪 M-Pesa STK Push Test")
    print("="*60)
    
    # Step 1: Get auth token (you'll need to authenticate first)
    print_step(1, "Authentication")
    token = input("Enter JWT token (or press Enter to skip and use existing): ").strip()
    
    if not token:
        print("⚠️  No token provided. Please authenticate first:")
        print("   1. Request OTP: POST /api/v1/auth/otp/request")
        print("   2. Verify OTP: POST /api/v1/auth/otp/verify")
        print("   3. Use the access_token from response")
        return
    
    # Step 2: Get test parameters
    print_step(2, "Test Parameters")
    phone = input("Enter phone number (default: +254708374149): ").strip() or "+254708374149"
    amount = input("Enter amount (default: 100): ").strip() or "100"
    account_ref = input("Enter account reference (default: TEST-STK-001): ").strip() or "TEST-STK-001"
    transaction_desc = input("Enter transaction description (default: Test Payment): ").strip() or "Test Payment"
    
    # Step 3: Initiate STK Push
    print_step(3, "Initiating STK Push")
    url = f"{BASE_URL}/api/v1/mpesa/pay"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "phone": phone,
        "amount": float(amount),
        "account_reference": account_ref,
        "transaction_desc": transaction_desc
    }
    
    print(f"📤 Request URL: {url}")
    print(f"📤 Request Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"📥 Response: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            checkout_id = result.get("checkout_request_id")
            print(f"\n✅ STK Push initiated successfully!")
            print(f"📱 Checkout Request ID: {checkout_id}")
            print(f"💬 Customer Message: {result.get('customer_message')}")
            print(f"\n📱 CHECK YOUR PHONE!")
            print(f"   You should receive an M-Pesa STK Push prompt")
            print(f"   Enter your M-Pesa PIN to complete the payment")
            print(f"\n🔍 To check payment status:")
            print(f"   curl -X GET {BASE_URL}/api/v1/mpesa/callback")
            return True
        else:
            print(f"\n❌ STK Push failed!")
            print(f"   Error: {result.get('message')}")
            print(f"   Code: {result.get('code')}")
            return False
            
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"   Error: {json.dumps(error_data, indent=2)}")
        except:
            print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stk_push()
    sys.exit(0 if success else 1)

