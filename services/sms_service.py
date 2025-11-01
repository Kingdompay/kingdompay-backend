"""
SMS service for KingdomPay
Handles sending OTP and notification SMS with multiple provider support
"""

import requests
import os
import json
import logging
from flask import current_app
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service for sending OTP and notifications with multiple provider support"""

    def __init__(self):
        self.api_key = os.environ.get("SMS_PROVIDER_API_KEY")
        self.api_url = os.environ.get("SMS_PROVIDER_URL")
        self.sender_id = os.environ.get("SMS_SENDER_ID", "KingdomPay")
        self.provider = os.environ.get(
            "SMS_PROVIDER", "generic"
        )  # generic, africastalking, twilio
        self.timeout = int(os.environ.get("SMS_TIMEOUT", 30))

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS message using configured provider"""
        # In development, just log the message
        if current_app.config.get("FLASK_ENV") == "development":
            logger.info(f"SMS to {phone_number}: {message}")
            return {
                "success": True,
                "message_id": "dev-message-id",
                "message": "SMS sent (development mode)",
            }

        # If no SMS provider configured, return success for development
        if not self.api_key or not self.api_url:
            logger.warning(
                f"No SMS provider configured. Would send to {phone_number}: {message}"
            )
            return {
                "success": True,
                "message_id": "no-provider-message-id",
                "message": "SMS sent (no provider configured)",
            }

        try:
            # Route to appropriate provider
            if self.provider == "africastalking":
                return self._send_africastalking_sms(phone_number, message)
            elif self.provider == "twilio":
                return self._send_twilio_sms(phone_number, message)
            else:
                return self._send_generic_sms(phone_number, message)

        except requests.exceptions.RequestException as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {"success": False, "message": f"SMS sending failed: {str(e)}"}
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {"success": False, "message": f"SMS sending failed: {str(e)}"}

    def _send_africastalking_sms(
        self, phone_number: str, message: str
    ) -> Dict[str, Any]:
        """Send SMS using Africa's Talking API"""
        headers = {
            "apiKey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "username": os.environ.get("SMS_USERNAME", "sandbox"),
            "to": phone_number,
            "message": message,
            "from": self.sender_id,
        }

        response = requests.post(
            f"{self.api_url}/messaging",
            headers=headers,
            data=data,
            timeout=self.timeout,
        )

        if response.status_code == 201:
            result = response.json()
            return {
                "success": True,
                "message_id": result.get("SMSMessageData", {})
                .get("Recipients", [{}])[0]
                .get("messageId"),
                "message": "SMS sent successfully via Africa's Talking",
            }
        else:
            logger.error(
                f"Africa's Talking SMS failed: {response.status_code} - {response.text}"
            )
            return {
                "success": False,
                "message": f"SMS sending failed: {response.status_code}",
            }

    def _send_twilio_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS using Twilio API"""
        from twilio.rest import Client

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_FROM_NUMBER")

        if not all([account_sid, auth_token, from_number]):
            return {
                "success": False,
                "message": "Twilio credentials not configured",
            }

        client = Client(account_sid, auth_token)

        try:
            message_obj = client.messages.create(
                body=message, from_=from_number, to=phone_number
            )

            return {
                "success": True,
                "message_id": message_obj.sid,
                "message": "SMS sent successfully via Twilio",
            }
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return {
                "success": False,
                "message": f"SMS sending failed: {str(e)}",
            }

    def _send_generic_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS using generic API format"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {"to": phone_number, "message": message, "sender_id": self.sender_id}

        response = requests.post(
            f"{self.api_url}/send", headers=headers, json=data, timeout=self.timeout
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message_id": result.get("message_id"),
                "message": "SMS sent successfully",
            }
        else:
            logger.error(
                f"Generic SMS failed: {response.status_code} - {response.text}"
            )
            return {
                "success": False,
                "message": f"SMS sending failed: {response.status_code}",
            }

    def send_otp_sms(self, phone_number, otp_code):
        """Send OTP SMS with formatted message"""
        message = f"Your KingdomPay verification code is: {otp_code}. Valid for 5 minutes. Do not share this code with anyone."
        return self.send_sms(phone_number, message)

    def send_notification_sms(self, phone_number, message):
        """Send notification SMS"""
        formatted_message = f"KingdomPay: {message}"
        return self.send_sms(phone_number, formatted_message)
