#!/usr/bin/env python3
"""
Test script for M-Pesa C2B (Customer to Business)
Tests C2B URL registration and payment simulation
"""

import os
import sys
import requests
import json

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

def test_c2b_registration():
    """Test C2B URL registration"""
    print("\n" + "="*60)
    print("🧪 M-Pesa C2B URL Registration Test")
    print("="*60)
    
    print("\n⚠️  Note: C2B URL registration requires M-Pesa API credentials")
    print("   This test will register validation and confirmation URLs")
    
    # Check if credentials are set
    consumer_key = os.environ.get('MPESA_CONSUMER_KEY')
    consumer_secret = os.environ.get('MPESA_CONSUMER_SECRET')
    
    if not consumer_key or not consumer_secret:
        print("\n❌ M-Pesa credentials not found in environment")
        print("   Please set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET")
        return False
    
    print(f"\n✅ M-Pesa credentials found")
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
    
    print(f"\n📋 URLs to register:")
    print(f"   Validation: {validation_url}")
    print(f"   Confirmation: {confirmation_url}")
    
    proceed = input("\nProceed with registration? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Cancelled")
        return False
    
    # Import and use C2B service
    try:
        from services.providers.mpesa.c2b import MpesaC2B
        
        c2b = MpesaC2B()
        result = c2b.register_urls(
            validation_url=validation_url,
            confirmation_url=confirmation_url
        )
        
        if result.get("success"):
            print(f"\n✅ C2B URLs registered successfully!")
            print(f"   Response: {result.get('response_description')}")
            return True
        else:
            print(f"\n❌ C2B URL registration failed!")
            print(f"   Error: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_c2b_simulation():
    """Test C2B payment simulation (sandbox only)"""
    print("\n" + "="*60)
    print("🧪 M-Pesa C2B Payment Simulation Test")
    print("="*60)
    
    print("\n⚠️  Note: This simulates a C2B payment (sandbox only)")
    
    # Get test parameters
    print_step(1, "Test Parameters")
    phone = input("Enter phone number (default: +254708374149): ").strip() or "+254708374149"
    amount = input("Enter amount (default: 100): ").strip() or "100"
    bill_ref = input("Enter bill reference (default: TEST-C2B-001): ").strip() or "TEST-C2B-001"
    
    # Import and use C2B service
    try:
        from services.providers.mpesa.c2b import MpesaC2B
        
        c2b = MpesaC2B()
        result = c2b.simulate_c2b_payment(
            phone=phone,
            amount=float(amount),
            bill_reference=bill_ref
        )
        
        if result.get("success"):
            print(f"\n✅ C2B payment simulated successfully!")
            print(f"   Response: {result.get('response_description')}")
            print(f"   Conversation ID: {result.get('conversation_id')}")
            print(f"\n📱 Check your validation and confirmation endpoints")
            print(f"   Validation: {BASE_URL}/api/v1/mpesa/validation")
            print(f"   Confirmation: {BASE_URL}/api/v1/mpesa/confirmation")
            return True
        else:
            print(f"\n❌ C2B simulation failed!")
            print(f"   Error: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test M-Pesa C2B functionality')
    parser.add_argument('--register', action='store_true', help='Test C2B URL registration')
    parser.add_argument('--simulate', action='store_true', help='Test C2B payment simulation')
    
    args = parser.parse_args()
    
    if args.register:
        success = test_c2b_registration()
    elif args.simulate:
        success = test_c2b_simulation()
    else:
        print("Choose a test:")
        print("1. Register C2B URLs")
        print("2. Simulate C2B Payment")
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            success = test_c2b_registration()
        elif choice == "2":
            success = test_c2b_simulation()
        else:
            print("Invalid choice")
            success = False
    
    sys.exit(0 if success else 1)

