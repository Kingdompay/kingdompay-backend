#!/usr/bin/env python3
"""
Test SMS Configuration
Verifies SMS provider is properly configured and can send test messages
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, '.env'))

from services.sms_service import SMSService
from app import create_app


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)


def test_sms_configuration():
    """Test SMS service configuration"""
    print_header("SMS Configuration Test")
    
    app = create_app()
    with app.app_context():
        sms_service = SMSService()
        
        print("\n📋 Configuration Check:")
        print(f"   Provider: {sms_service.provider}")
        print(f"   API Key: {'✅ Set' if sms_service.api_key else '❌ Not set'}")
        print(f"   API URL: {sms_service.api_url or '❌ Not set'}")
        print(f"   Sender ID: {sms_service.sender_id}")
        print(f"   Timeout: {sms_service.timeout}s")
        
        # Provider-specific checks
        if sms_service.provider == "africastalking":
            username = os.environ.get("SMS_USERNAME")
            print(f"   Username: {username or '❌ Not set'}")
            if not username:
                print("   ⚠️  SMS_USERNAME required for Africa's Talking")
        
        elif sms_service.provider == "twilio":
            account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
            from_number = os.environ.get("TWILIO_FROM_NUMBER")
            print(f"   Account SID: {'✅ Set' if account_sid else '❌ Not set'}")
            print(f"   Auth Token: {'✅ Set' if auth_token else '❌ Not set'}")
            print(f"   From Number: {from_number or '❌ Not set'}")
            if not all([account_sid, auth_token, from_number]):
                print("   ⚠️  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER required")
        
        # Check if configuration is complete
        if sms_service.provider == "africastalking":
            is_configured = bool(sms_service.api_key and sms_service.api_url and os.environ.get("SMS_USERNAME"))
        elif sms_service.provider == "twilio":
            is_configured = bool(
                os.environ.get("TWILIO_ACCOUNT_SID") and
                os.environ.get("TWILIO_AUTH_TOKEN") and
                os.environ.get("TWILIO_FROM_NUMBER")
            )
        else:  # generic
            is_configured = bool(sms_service.api_key and sms_service.api_url)
        
        if is_configured:
            print("\n✅ SMS Configuration: Complete")
            return True
        else:
            print("\n❌ SMS Configuration: Incomplete")
            print("\n📝 Required Environment Variables:")
            if sms_service.provider == "africastalking":
                print("   - SMS_PROVIDER=africastalking")
                print("   - SMS_PROVIDER_API_KEY")
                print("   - SMS_PROVIDER_URL")
                print("   - SMS_USERNAME")
            elif sms_service.provider == "twilio":
                print("   - SMS_PROVIDER=twilio")
                print("   - TWILIO_ACCOUNT_SID")
                print("   - TWILIO_AUTH_TOKEN")
                print("   - TWILIO_FROM_NUMBER")
            else:
                print("   - SMS_PROVIDER=generic")
                print("   - SMS_PROVIDER_API_KEY")
                print("   - SMS_PROVIDER_URL")
            return False


def test_sms_sending(test_phone=None):
    """Test sending an SMS"""
    print_header("SMS Sending Test")
    
    if not test_phone:
        test_phone = input("\nEnter test phone number (e.g., +254712345678): ").strip()
        if not test_phone:
            print("❌ No phone number provided. Skipping send test.")
            return False
    
    app = create_app()
    with app.app_context():
        sms_service = SMSService()
        
        # Check if configured
        if not sms_service.api_key or not sms_service.api_url:
            print("⚠️  SMS provider not configured. Running in development mode.")
            print("   SMS will be logged but not actually sent.")
        
        print(f"\n📤 Sending test SMS to {test_phone}...")
        test_message = "Test message from KingdomPay SMS service. If you receive this, SMS is working correctly!"
        
        result = sms_service.send_sms(test_phone, test_message)
        
        if result.get("success"):
            print("✅ SMS sent successfully!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   Response: {result.get('message', 'N/A')}")
            return True
        else:
            print("❌ SMS sending failed!")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            return False


def test_otp_sms(test_phone=None):
    """Test OTP SMS format"""
    print_header("OTP SMS Format Test")
    
    if not test_phone:
        test_phone = input("\nEnter test phone number (e.g., +254712345678): ").strip()
        if not test_phone:
            print("❌ No phone number provided. Skipping OTP test.")
            return False
    
    app = create_app()
    with app.app_context():
        sms_service = SMSService()
        
        test_otp = "123456"
        print(f"\n📤 Sending OTP SMS to {test_phone}...")
        
        result = sms_service.send_otp_sms(test_phone, test_otp)
        
        if result.get("success"):
            print("✅ OTP SMS sent successfully!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   OTP Code: {test_otp}")
            return True
        else:
            print("❌ OTP SMS sending failed!")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            return False


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("🚀 SMS Configuration Test Suite")
    print("="*60)
    
    # Test 1: Configuration
    config_ok = test_sms_configuration()
    
    if not config_ok:
        print("\n⚠️  Please configure SMS provider before testing sending.")
        print("   See docs/SMS_SETUP_GUIDE.md for instructions.")
        return
    
    # Test 2: Send test SMS (optional)
    print("\n" + "-"*60)
    send_test = input("\nSend test SMS? (y/n): ").strip().lower()
    if send_test == 'y':
        test_sms_sending()
    
    # Test 3: Send OTP SMS (optional)
    print("\n" + "-"*60)
    send_otp = input("\nSend test OTP SMS? (y/n): ").strip().lower()
    if send_otp == 'y':
        test_otp_sms()
    
    print("\n" + "="*60)
    print("✅ SMS Configuration Test Complete")
    print("="*60)


if __name__ == "__main__":
    main()







