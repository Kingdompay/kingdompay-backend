"""
Airtel Money provider adapter
"""

import os
import base64
import requests
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from services.providers.base import ProviderAdapter, ProviderInitResponse, PayoutResponse


class AirtelAdapter(ProviderAdapter):
    """Airtel Money payment adapter"""

    def __init__(self):
        self.client_id = os.environ.get("AIRTEL_CLIENT_ID")
        self.client_secret = os.environ.get("AIRTEL_CLIENT_SECRET")
        self.base_url = os.environ.get("AIRTEL_BASE_URL", "https://openapiuat.airtel.africa")
        self.callback_url = os.environ.get("AIRTEL_CALLBACK_URL", "")
        self._access_token = None

    def _get_access_token(self) -> Optional[str]:
        """Obtain OAuth token from Airtel"""
        if self._access_token:
            return self._access_token
        
        url = f"{self.base_url}/auth/oauth2/token"
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
                json={"grant_type": "client_credentials"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access_token")
                return self._access_token
        except Exception as e:
            current_app.logger.exception("Failed to get Airtel access token")
        return None

    def initiate_debit(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> ProviderInitResponse:
        """Initiate Airtel Money collection (USSD Push)"""
        token = self._get_access_token()
        if not token:
            return ProviderInitResponse(False, message="Failed to authenticate with Airtel")

        # Format phone (remove + and ensure country code)
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/standard/v1/disbursements/"
        # For collections, use collections endpoint
        collection_url = f"{self.base_url}/standard/v1/payments/"
        
        payload = {
            "payee": {
                "msisdn": phone_clean
            },
            "reference": reference[:50],
            "transaction": {
                "amount": str(int(float(amount))),
                "id": reference
            }
        }

        try:
            resp = requests.post(
                collection_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Country": "KE",
                    "X-Currency": currency,
                },
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                transaction_id = data.get("data", {}).get("transaction", {}).get("id")
                if transaction_id:
                    return ProviderInitResponse(True, provider_ref=transaction_id)
                error_msg = data.get("status", {}).get("message", resp.text)
                return ProviderInitResponse(False, message=error_msg)
            return ProviderInitResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("Airtel collection failed")
            return ProviderInitResponse(False, message=str(e))

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Airtel webhook callback"""
        status = payload.get("status", {}).get("success")
        transaction_id = payload.get("data", {}).get("transaction", {}).get("id")
        
        if status is True:
            return {
                "status": "SUCCESS",
                "provider_ref": transaction_id,
                "amount": payload.get("data", {}).get("transaction", {}).get("amount"),
            }
        return {
            "status": "FAILED",
            "provider_ref": transaction_id,
            "message": payload.get("status", {}).get("message", "Payment failed"),
        }

    def payout(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> PayoutResponse:
        """Payout via Airtel Money"""
        token = self._get_access_token()
        if not token:
            return PayoutResponse(False, message="Failed to authenticate with Airtel")

        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/standard/v1/disbursements/"
        
        payload = {
            "payee": {
                "msisdn": phone_clean
            },
            "reference": reference[:50],
            "transaction": {
                "amount": str(int(float(amount))),
                "id": reference
            }
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Country": "KE",
                    "X-Currency": currency,
                },
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                transaction_id = data.get("data", {}).get("transaction", {}).get("id")
                if transaction_id:
                    return PayoutResponse(True, provider_ref=transaction_id)
                error_msg = data.get("status", {}).get("message", resp.text)
                return PayoutResponse(False, message=error_msg)
            return PayoutResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("Airtel payout failed")
            return PayoutResponse(False, message=str(e))

    def refund(
        self, *, provider_ref: str, amount: Decimal, reason: str
    ) -> PayoutResponse:
        """Refund via reversal (if supported by Airtel API)"""
        # Airtel Money refund typically requires manual processing
        # This is a placeholder - implement based on Airtel API docs
        return PayoutResponse(False, message="Refund not yet implemented for Airtel")

