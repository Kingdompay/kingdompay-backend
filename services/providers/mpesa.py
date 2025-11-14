"""
M-Pesa (Daraja) payment provider adapter
Implements ProviderAdapter interface for integration with ProviderService
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from flask import current_app
from services.providers.base import ProviderAdapter, ProviderInitResponse, PayoutResponse
from services.providers.mpesa.auth import MpesaAuth
from services.providers.mpesa.stk_push import MpesaSTKPush
from services.providers.mpesa.c2b import MpesaC2B


class MpesaAdapter(ProviderAdapter):
    """M-Pesa payment provider adapter implementing ProviderAdapter interface"""

    def __init__(self):
        self.auth = MpesaAuth()
        self.stk_push = MpesaSTKPush()
        self.c2b = MpesaC2B()

    def initiate_debit(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> ProviderInitResponse:
        """
        Initiate a debit (STK Push) to collect funds from customer
        
        Args:
            phone: Customer phone number
            amount: Amount to collect
            currency: Currency code (should be KES for M-Pesa)
            reference: Unique transaction reference
            
        Returns:
            ProviderInitResponse with success status and checkout_request_id
        """
        if currency != "KES":
            return ProviderInitResponse(
                False, message=f"M-Pesa only supports KES, got {currency}"
            )

        result = self.stk_push.initiate_stk_push(
            phone=phone,
            amount=amount,
            account_reference=reference,
            transaction_desc="Payment",
        )

        if result.get("success"):
            checkout_request_id = result.get("checkout_request_id")
            return ProviderInitResponse(
                True, provider_ref=checkout_request_id, message=result.get("customer_message")
            )
        else:
            return ProviderInitResponse(False, message=result.get("message", "STK Push failed"))

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate M-Pesa webhook payload (STK callback)
        
        Args:
            payload: Raw webhook payload from M-Pesa
            
        Returns:
            Parsed webhook event with status and provider_ref
        """
        # Handle STK Push callback
        body = payload.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        
        if stk_callback:
            result_code = stk_callback.get("ResultCode")
            checkout_request_id = body.get("CheckoutRequestID") or stk_callback.get("CheckoutRequestID")
            
            if result_code == 0:
                # Success
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                items = callback_metadata.get("Item", [])
                
                # Extract receipt number and other details
                receipt_number = None
                amount = None
                phone = None
                
                for item in items:
                    name = item.get("Name")
                    value = item.get("Value")
                    if name == "MpesaReceiptNumber":
                        receipt_number = value
                    elif name == "Amount":
                        amount = value
                    elif name == "PhoneNumber":
                        phone = value
                
                return {
                    "status": "SUCCESS",
                    "provider_ref": receipt_number,
                    "checkout_request_id": checkout_request_id,
                    "amount": amount,
                    "phone": phone,
                }
            else:
                # Failed
                result_desc = stk_callback.get("ResultDesc", "Payment failed")
                return {
                    "status": "FAILED",
                    "provider_ref": checkout_request_id,
                    "checkout_request_id": checkout_request_id,
                    "message": result_desc,
                }
        
        # Handle C2B confirmation (if needed)
        trans_id = payload.get("TransID")
        if trans_id:
            trans_amount = payload.get("TransAmount")
            return {
                "status": "SUCCESS",
                "provider_ref": trans_id,
                "amount": trans_amount,
            }
        
        # Unknown payload format
        current_app.logger.warning(f"Unknown M-Pesa webhook payload format: {payload}")
        return {
            "status": "UNKNOWN",
            "provider_ref": None,
            "message": "Unknown webhook payload format",
        }

    def payout(
        self, *, phone: str, amount: Decimal, currency: str, reference: str
    ) -> PayoutResponse:
        """
        Initiate a payout (B2C) to recipient
        Note: B2C API implementation can be added here later
        
        Args:
            phone: Recipient phone number
            amount: Payout amount
            currency: Currency code
            reference: Unique transaction reference
            
        Returns:
            PayoutResponse with success status
        """
        # B2C implementation can be added here
        # For now, return not implemented
        return PayoutResponse(
            False, message="M-Pesa B2C payout not yet implemented. Use B2C API separately."
        )

    def refund(
        self, *, provider_ref: str, amount: Decimal, reason: str
    ) -> PayoutResponse:
        """
        Refund a transaction
        Note: Transaction reversal API implementation can be added here later
        
        Args:
            provider_ref: Original transaction reference
            amount: Refund amount
            reason: Refund reason
            
        Returns:
            PayoutResponse with success status
        """
        # Transaction reversal implementation can be added here
        return PayoutResponse(
            False, message="M-Pesa refund not yet implemented. Use reversal API separately."
        )
