#!/usr/bin/env python3
"""
Non-interactive M-Pesa Integration Test Script
Tests STK Push and C2B functionality
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

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def print_step(step, message):
    """Print formatted step"""
    print(f"\n{step}: {message}")

def test_c2b_registration():
    """Test C2B URL registration"""
    print_header("C2B URL Registration Test")
    
    # Check credentials
    consumer_key = os.environ.get('MPESA_CONSUMER_KEY')
    consumer_secret = os.environ.get('MPESA_CONSUMER_SECRET')
    
    if not consumer_key or not consumer_secret:
        print("❌ M-Pesa credentials not found")
        return False
    
    print_step("1️⃣", "Checking credentials")
    print(f"   Consumer Key: {consumer_key[:10]}...")
    
    # Get URLs
    validation_url = os.environ.get(
        'MPESA_C2B_VALIDATION_URL',
        f'{BASE_URL}/api/v1/mpesa/validation'
    )
    confirmation_url = os.environ.get(
        'MPESA_C2B_CONFIRMATION_URL',
        f'{BASE_URL}/api/v1/mpesa/confirmation'
    )
    
    print_step("2️⃣", "Registering URLs")
    print(f"   Validation: {validation_url}")
    print(f"   Confirmation: {confirmation_url}")
    
    try:
        from services.providers.mpesa.c2b import MpesaC2B
        
        c2b = MpesaC2B()
        result = c2b.register_urls(
            validation_url=validation_url,
            confirmation_url=confirmation_url
        )
        
        if result.get("success"):
            print("\n✅ C2B URLs registered successfully!")
            print(f"   Response: {result.get('response_description')}")
            return True
        else:
            print(f"\n❌ C2B URL registration failed!")
            print(f"   Error: {result.get('message')}")
            if result.get('response_code'):
                print(f"   Response Code: {result.get('response_code')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_c2b_simulation():
    """Test C2B payment simulation"""
    print_header("C2B Payment Simulation Test")
    
    print_step("1️⃣", "Simulating C2B payment")
    phone = "+254708374149"
    amount = 100
    bill_ref = f"TEST-C2B-{int(__import__('time').time())}"
    
    print(f"   Phone: {phone}")
    print(f"   Amount: {amount}")
    print(f"   Bill Reference: {bill_ref}")
    
    try:
        from services.providers.mpesa.c2b import MpesaC2B
        
        c2b = MpesaC2B()
        result = c2b.simulate_c2b_payment(
            phone=phone,
            amount=float(amount),
            bill_reference=bill_ref
        )
        
        if result.get("success"):
            print("\n✅ C2B payment simulated successfully!")
            print(f"   Response: {result.get('response_description')}")
            print(f"   Conversation ID: {result.get('conversation_id')}")
            print(f"\n📱 Check validation and confirmation endpoints for callbacks")
            return True
        else:
            print(f"\n❌ C2B simulation failed!")
            print(f"   Error: {result.get('message')}")
            if result.get('response_code'):
                print(f"   Response Code: {result.get('response_code')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_stk_push_auth():
    """Test STK Push authentication (requires manual token)"""
    print_header("STK Push Authentication Test")
    
    print("⚠️  This test requires manual authentication")
    print("\nTo get a token:")
    print("1. Request OTP:")
    print(f"   curl -X POST {BASE_URL}/api/v1/auth/otp/request \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"phone": "+254708374149"}\'')
    print("\n2. Verify OTP:")
    print(f"   curl -X POST {BASE_URL}/api/v1/auth/otp/verify \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"phone_number": "+254708374149", "otp_code": "YOUR_OTP"}\'')
    print("\n3. Use the access_token from the response")
    print("\n4. Then test STK Push:")
    print(f"   curl -X POST {BASE_URL}/api/v1/mpesa/pay \\")
    print('     -H "Authorization: Bearer YOUR_TOKEN" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"phone": "+254708374149", "amount": 100, "account_reference": "TEST-001"}\'')
    
    return None

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 M-Pesa Integration Test Suite")
    print("="*60)
    
    # Check server
    print("\n1️⃣  Checking server...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️  Server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False
    
    results = {}
    
    # Test C2B Registration
    print("\n" + "-"*60)
    results['c2b_registration'] = test_c2b_registration()
    
    # Test C2B Simulation
    print("\n" + "-"*60)
    results['c2b_simulation'] = test_c2b_simulation()
    
    # STK Push info
    print("\n" + "-"*60)
    test_stk_push_auth()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    for test_name, result in results.items():
        if result is True:
            print(f"✅ {test_name}: PASSED")
        elif result is False:
            print(f"❌ {test_name}: FAILED")
        else:
            print(f"⏭️  {test_name}: SKIPPED")
    
    return all(r for r in results.values() if r is not None)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

