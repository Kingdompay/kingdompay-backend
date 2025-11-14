"""
M-Pesa (Daraja) payment provider module
"""

from .auth import MpesaAuth
from .stk_push import MpesaSTKPush
from .c2b import MpesaC2B

# Import MpesaAdapter from the mpesa.py file in parent directory
# Use importlib to avoid circular imports
import importlib.util
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mpesa_file = os.path.join(parent_dir, "mpesa.py")

if os.path.exists(mpesa_file):
    spec = importlib.util.spec_from_file_location("_mpesa_adapter", mpesa_file)
    _mpesa_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mpesa_module)
    MpesaAdapter = _mpesa_module.MpesaAdapter
else:
    # If mpesa.py doesn't exist, define a minimal adapter
    from decimal import Decimal
    from typing import Dict, Any
    from services.providers.base import ProviderAdapter, ProviderInitResponse, PayoutResponse
    
    class MpesaAdapter(ProviderAdapter):
        """M-Pesa payment provider adapter"""
        def __init__(self):
            self.auth = MpesaAuth()
            self.stk_push = MpesaSTKPush()
            self.c2b = MpesaC2B()
        
        def initiate_debit(self, *, phone: str, amount: Decimal, currency: str, reference: str):
            if currency != "KES":
                return ProviderInitResponse(False, message="M-Pesa only supports KES")
            result = self.stk_push.initiate_stk_push(phone=phone, amount=amount, account_reference=reference)
            if result.get("success"):
                return ProviderInitResponse(True, provider_ref=result.get("checkout_request_id"))
            return ProviderInitResponse(False, message=result.get("message"))
        
        def handle_webhook(self, payload: Dict[str, Any]):
            body = payload.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            if stk_callback:
                result_code = stk_callback.get("ResultCode")
                checkout_request_id = body.get("CheckoutRequestID")
                if result_code == 0:
                    callback_metadata = stk_callback.get("CallbackMetadata", {})
                    items = callback_metadata.get("Item", [])
                    receipt_number = None
                    for item in items:
                        if item.get("Name") == "MpesaReceiptNumber":
                            receipt_number = item.get("Value")
                            break
                    return {"status": "SUCCESS", "provider_ref": receipt_number, "checkout_request_id": checkout_request_id}
                return {"status": "FAILED", "provider_ref": checkout_request_id, "message": stk_callback.get("ResultDesc")}
            return {"status": "UNKNOWN", "provider_ref": None}
        
        def payout(self, *, phone: str, amount: Decimal, currency: str, reference: str):
            return PayoutResponse(False, message="B2C not yet implemented")
        
        def refund(self, *, provider_ref: str, amount: Decimal, reason: str):
            return PayoutResponse(False, message="Refund not yet implemented")

__all__ = ["MpesaAuth", "MpesaSTKPush", "MpesaC2B", "MpesaAdapter"]

