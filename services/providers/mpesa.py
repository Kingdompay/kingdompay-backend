"""
M-Pesa (Daraja) provider adapter
"""

import os
import base64
import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from services.providers.base import ProviderAdapter, ProviderInitResponse, PayoutResponse


class MpesaAdapter(ProviderAdapter):
    """M-Pesa STK Push and B2C adapter via Safaricom Daraja API"""

    def __init__(self):
        self.consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")
        self.passkey = os.environ.get("MPESA_PASSKEY")
        self.shortcode = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name = os.environ.get("MPESA_INITIATOR_NAME", "")
        self.security_credential = os.environ.get("MPESA_SECURITY_CREDENTIAL", "")
        self.b2c_shortcode = os.environ.get("MPESA_B2C_SHORTCODE", self.shortcode)
        self.base_url = os.environ.get("MPESA_BASE_URL", "https://sandbox.safaricom.co.ke")
        self.callback_url = os.environ.get("MPESA_CALLBACK_URL", "")
        self.b2c_callback_url = os.environ.get("MPESA_B2C_CALLBACK_URL", "")
        self._access_token = None

    def _get_access_token(self) -> Optional[str]:
        """Obtain OAuth token from Daraja"""
        if self._access_token:
            return self._access_token
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        try:
            resp = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access_token")
                return self._access_token
        except Exception as e:
            current_app.logger.exception("Failed to get M-Pesa access token")
        return None

    def initiate_debit(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> ProviderInitResponse:
        """Initiate STK Push"""
        token = self._get_access_token()
        if not token:
            return ProviderInitResponse(False, message="Failed to authenticate with M-Pesa")

        # Format phone (remove + and ensure 254 prefix)
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        # Generate current timestamp in format YYYYMMDDHHmmss
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Generate password: base64(BusinessShortCode + Passkey + Timestamp)
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": phone_clean,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_clean,
            "CallBackURL": self.callback_url,
            "AccountReference": reference[:20],
            "TransactionDesc": "KingdomPay Payment",
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                checkout_id = data.get("CheckoutRequestID")
                if checkout_id:
                    return ProviderInitResponse(True, provider_ref=checkout_id)
                error_msg = data.get("errorMessage", resp.text)
                return ProviderInitResponse(False, message=error_msg)
            return ProviderInitResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("M-Pesa STK Push failed")
            return ProviderInitResponse(False, message=str(e))

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse M-Pesa STK callback"""
        result_code = payload.get("Body", {}).get("stkCallback", {}).get("ResultCode")
        checkout_id = payload.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
        merchant_req_id = payload.get("Body", {}).get("stkCallback", {}).get("MerchantRequestID")
        if result_code == 0:
            callback_meta = payload.get("Body", {}).get("stkCallback", {}).get("CallbackMetadata", {}).get("Item", [])
            mpesa_receipt = next((i.get("Value") for i in callback_meta if i.get("Name") == "MpesaReceiptNumber"), None)
            amount = next((i.get("Value") for i in callback_meta if i.get("Name") == "Amount"), None)
            return {
                "status": "SUCCESS",
                "provider_ref": mpesa_receipt or checkout_id,
                "checkout_request_id": checkout_id,
                "amount": amount,
            }
        return {"status": "FAILED", "provider_ref": checkout_id, "message": "Payment cancelled or failed"}

    def payout(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> PayoutResponse:
        """B2C payout via M-Pesa API"""
        token = self._get_access_token()
        if not token:
            return PayoutResponse(False, message="Failed to authenticate with M-Pesa")

        if not self.initiator_name or not self.security_credential:
            return PayoutResponse(False, message="B2C credentials not configured")

        # Format phone (remove + and ensure 254 prefix)
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        
        payload = {
            "InitiatorName": self.initiator_name,
            "SecurityCredential": self.security_credential,
            "CommandID": "BusinessPayment",
            "Amount": int(float(amount)),
            "PartyA": self.b2c_shortcode,
            "PartyB": phone_clean,
            "Remarks": reference[:100],
            "QueueTimeOutURL": self.b2c_callback_url,
            "ResultURL": self.b2c_callback_url,
            "Occasion": "KingdomPay Payout",
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                conversation_id = data.get("ConversationID")
                originator_conversation_id = data.get("OriginatorConversationID")
                if conversation_id:
                    return PayoutResponse(True, provider_ref=conversation_id)
                error_msg = data.get("errorMessage", resp.text)
                return PayoutResponse(False, message=error_msg)
            return PayoutResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("M-Pesa B2C payout failed")
            return PayoutResponse(False, message=str(e))

    def refund(
        self, *, provider_ref: str, amount: Decimal, reason: str
    ) -> PayoutResponse:
        """Refund via transaction reversal API"""
        token = self._get_access_token()
        if not token:
            return PayoutResponse(False, message="Failed to authenticate with M-Pesa")

        if not self.initiator_name or not self.security_credential:
            return PayoutResponse(False, message="Reversal credentials not configured")

        url = f"{self.base_url}/mpesa/reversal/v1/request"
        
        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": self.security_credential,
            "CommandID": "TransactionReversal",
            "TransactionID": provider_ref,
            "Amount": int(float(amount)),
            "ReceiverParty": self.shortcode,
            "RecieverIdentifierType": "4",  # Organization
            "ResultURL": self.b2c_callback_url or self.callback_url,
            "QueueTimeOutURL": self.b2c_callback_url or self.callback_url,
            "Remarks": reason[:100] or "Refund",
            "Occasion": "Refund",
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                conversation_id = data.get("ConversationID")
                if conversation_id:
                    return PayoutResponse(True, provider_ref=conversation_id)
                error_msg = data.get("errorMessage", resp.text)
                return PayoutResponse(False, message=error_msg)
            return PayoutResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("M-Pesa refund failed")
            return PayoutResponse(False, message=str(e))

