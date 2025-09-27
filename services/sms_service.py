"""
SMS service for KingdomPay
Handles sending OTP and notification SMS
"""

import requests
import os
from flask import current_app


class SMSService:
    """SMS service for sending OTP and notifications"""

    def __init__(self):
        self.api_key = os.environ.get("SMS_PROVIDER_API_KEY")
        self.api_url = os.environ.get("SMS_PROVIDER_URL")
        self.sender_id = os.environ.get("SMS_SENDER_ID", "KingdomPay")

    def send_sms(self, phone_number, message):
        """Send SMS message"""
        # In development, just log the message
        if current_app.config.get("FLASK_ENV") == "development":
            print(f"SMS to {phone_number}: {message}")
            return {
                "success": True,
                "message_id": "dev-message-id",
                "message": "SMS sent (development mode)",
            }

        # If no SMS provider configured, return success for development
        if not self.api_key or not self.api_url:
            print(f"SMS to {phone_number}: {message}")
            return {
                "success": True,
                "message_id": "no-provider-message-id",
                "message": "SMS sent (no provider configured)",
            }

        try:
            # This is a generic implementation
            # You'll need to adapt this for your specific SMS provider
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {"to": phone_number, "message": message, "sender_id": self.sender_id}

            response = requests.post(
                f"{self.api_url}/send", headers=headers, json=data, timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "message": "SMS sent successfully",
                }
            else:
                return {
                    "success": False,
                    "message": f"SMS sending failed: {response.status_code}",
                }

        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"SMS sending failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"SMS sending failed: {str(e)}"}

    def send_otp_sms(self, phone_number, otp_code):
        """Send OTP SMS with formatted message"""
        message = f"Your KingdomPay verification code is: {otp_code}. Valid for 5 minutes. Do not share this code with anyone."
        return self.send_sms(phone_number, message)

    def send_notification_sms(self, phone_number, message):
        """Send notification SMS"""
        formatted_message = f"KingdomPay: {message}"
        return self.send_sms(phone_number, formatted_message)
