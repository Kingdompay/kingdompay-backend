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
from services.providers.mpesa.b2c import MpesaB2C


class MpesaAdapter(ProviderAdapter):
    """M-Pesa payment provider adapter implementing ProviderAdapter interface"""

    def __init__(self):
        self.auth = MpesaAuth()
        self.stk_push = MpesaSTKPush()
        self.c2b = MpesaC2B()
        self.b2c = MpesaB2C()

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
        
        # Handle B2C result callback
        result = payload.get("Result")
        if result:
            result_code = result.get("ResultCode")
            transaction_id = result.get("TransactionID")
            originator_conversation_id = result.get("OriginatorConversationID")
            
            # Parse result parameters
            result_parameters = result.get("ResultParameters", {})
            result_parameter = result_parameters.get("ResultParameter", [])
            
            transaction_receipt = None
            transaction_amount = None
            
            for param in result_parameter:
                key = param.get("Key")
                value = param.get("Value")
                if key == "TransactionReceipt":
                    transaction_receipt = value
                elif key == "TransactionAmount":
                    transaction_amount = value
            
            if result_code == "0":
                # Success
                return {
                    "status": "SUCCESS",
                    "provider_ref": transaction_receipt or transaction_id,
                    "conversation_id": originator_conversation_id,
                    "amount": transaction_amount,
                }
            else:
                # Failed
                result_desc = result.get("ResultDesc", "B2C payout failed")
                return {
                    "status": "FAILED",
                    "provider_ref": transaction_id or originator_conversation_id,
                    "conversation_id": originator_conversation_id,
                    "message": result_desc,
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
        
        Args:
            phone: Recipient phone number
            amount: Payout amount
            currency: Currency code (should be KES for M-Pesa)
            reference: Unique transaction reference (used as remarks)
            
        Returns:
            PayoutResponse with success status and conversation_id
        """
        if currency != "KES":
            return PayoutResponse(
                False, message=f"M-Pesa only supports KES, got {currency}"
            )

        result = self.b2c.initiate_payout(
            phone=phone,
            amount=amount,
            remarks=reference[:100] if reference else "Payout",
            command_id="BusinessPayment",
        )

        if result.get("success"):
            conversation_id = result.get("conversation_id")
            return PayoutResponse(
                True,
                provider_ref=conversation_id,
                message=result.get("response_description", "B2C payout initiated"),
            )
        else:
            return PayoutResponse(
                False, message=result.get("message", "B2C payout failed")
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
