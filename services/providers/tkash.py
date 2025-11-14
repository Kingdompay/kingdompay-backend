"""
T-Kash (Telecom Kenya) provider adapter
"""

import os
import base64
import requests
import json
from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from services.providers.base import (
    ProviderAdapter,
    ProviderInitResponse,
    PayoutResponse,
)


class TKashAdapter(ProviderAdapter):
    """T-Kash mobile money adapter"""

    def __init__(self):
        self.api_key = os.environ.get("TKASH_API_KEY")
        self.api_secret = os.environ.get("TKASH_API_SECRET")
        self.merchant_id = os.environ.get("TKASH_MERCHANT_ID")
        self.base_url = os.environ.get("TKASH_BASE_URL", "https://api.t-kash.co.ke")
        self.callback_url = os.environ.get("TKASH_CALLBACK_URL", "")

    def _get_auth_header(self) -> str:
        """Generate authorization header"""
        # T-Kash typically uses API key in header or signature-based auth
        # Adjust based on actual T-Kash API documentation
        if self.api_key and self.api_secret:
            auth_str = f"{self.api_key}:{self.api_secret}"
            return f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        return f"Bearer {self.api_key}" if self.api_key else ""

    def initiate_debit(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> ProviderInitResponse:
        """Initiate T-Kash payment collection"""
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/v1/payments/request"

        payload = {
            "merchant_id": self.merchant_id,
            "phone_number": phone_clean,
            "amount": int(float(amount)),
            "currency": currency,
            "reference": reference[:50],
            "callback_url": self.callback_url,
            "description": "KingdomPay Payment",
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                transaction_id = data.get("transaction_id") or data.get("id")
                if transaction_id:
                    return ProviderInitResponse(True, provider_ref=transaction_id)
                error_msg = data.get("message") or data.get("error", resp.text)
                return ProviderInitResponse(False, message=error_msg)
            return ProviderInitResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("T-Kash collection failed")
            return ProviderInitResponse(False, message=str(e))

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse T-Kash webhook callback"""
        status = payload.get("status", "").upper()
        transaction_id = payload.get("transaction_id") or payload.get("id")

        if status == "SUCCESS" or status == "COMPLETED":
            return {
                "status": "SUCCESS",
                "provider_ref": transaction_id,
                "amount": payload.get("amount"),
            }
        return {
            "status": "FAILED",
            "provider_ref": transaction_id,
            "message": payload.get("message", "Payment failed"),
        }

    def payout(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> PayoutResponse:
        """Payout via T-Kash"""
        phone_clean = phone.replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"

        url = f"{self.base_url}/v1/payouts/request"

        payload = {
            "merchant_id": self.merchant_id,
            "phone_number": phone_clean,
            "amount": int(float(amount)),
            "currency": currency,
            "reference": reference[:50],
            "description": "KingdomPay Payout",
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                transaction_id = data.get("transaction_id") or data.get("id")
                if transaction_id:
                    return PayoutResponse(True, provider_ref=transaction_id)
                error_msg = data.get("message") or data.get("error", resp.text)
                return PayoutResponse(False, message=error_msg)
            return PayoutResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("T-Kash payout failed")
            return PayoutResponse(False, message=str(e))

    def refund(
        self, *, provider_ref: str, amount: Decimal, reason: str
    ) -> PayoutResponse:
        """Refund via T-Kash reversal"""
        url = f"{self.base_url}/v1/transactions/{provider_ref}/refund"

        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(float(amount)),
            "reason": reason[:200],
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                refund_id = data.get("refund_id") or data.get("transaction_id")
                if refund_id:
                    return PayoutResponse(True, provider_ref=refund_id)
                return PayoutResponse(
                    False, message=data.get("message", "Refund failed")
                )
            return PayoutResponse(False, message=resp.text)
        except Exception as e:
            current_app.logger.exception("T-Kash refund failed")
            return PayoutResponse(False, message=str(e))
