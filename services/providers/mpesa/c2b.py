"""
M-Pesa C2B (Customer to Business) API
Handles C2B URL registration, validation, and confirmation
"""

import os
import requests
from typing import Optional, Dict, Any
from .auth import MpesaAuth, get_logger


class MpesaC2B:
    """Handles M-Pesa C2B (Customer to Business) transactions"""

    def __init__(self):
        self.auth = MpesaAuth()
        self.base_url = os.environ.get(
            "MPESA_BASE_URL", "https://sandbox.safaricom.co.ke"
        )
        self.shortcode = os.environ.get("MPESA_SHORTCODE")
        self.validation_url = os.environ.get("MPESA_C2B_VALIDATION_URL")
        self.confirmation_url = os.environ.get("MPESA_C2B_CONFIRMATION_URL")
        self.response_type = os.environ.get("MPESA_C2B_RESPONSE_TYPE", "Completed")

    def register_urls(
        self,
        validation_url: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        response_type: str = "Completed",
    ) -> Dict[str, Any]:
        """
        Register C2B validation and confirmation URLs with M-Pesa
        
        Args:
            validation_url: URL for validation callbacks (defaults to env var)
            confirmation_url: URL for confirmation callbacks (defaults to env var)
            response_type: Response type - "Completed" or "Cancelled"
            
        Returns:
            Dictionary with registration result
        """
        if not self.shortcode:
            return {
                "success": False,
                "message": "M-Pesa shortcode not configured",
            }

        # Use provided URLs or fall back to environment variables
        validation = validation_url or self.validation_url
        confirmation = confirmation_url or self.confirmation_url

        if not validation or not confirmation:
            return {
                "success": False,
                "message": "Validation and confirmation URLs are required",
            }

        access_token = self.auth.get_access_token()
        if not access_token:
            return {
                "success": False,
                "message": "Failed to authenticate with M-Pesa API",
            }

        payload = {
            "ShortCode": self.shortcode,
            "ResponseType": response_type,
            "ConfirmationURL": confirmation,
            "ValidationURL": validation,
        }

        url = f"{self.base_url}/mpesa/c2b/v1/registerurl"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            get_logger().info(
                f"Registering C2B URLs: Validation={validation}, Confirmation={confirmation}"
            )
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            response_code = data.get("ResponseCode")

            if response_code == "0":
                get_logger().info("C2B URLs registered successfully")
                return {
                    "success": True,
                    "response_code": response_code,
                    "response_description": data.get("ResponseDescription"),
                }
            else:
                error_message = data.get("ResponseDescription", "Unknown error")
                get_logger().error(
                    f"C2B URL registration failed: {error_message}"
                )
                return {
                    "success": False,
                    "message": error_message,
                    "response_code": response_code,
                }

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("errorMessage", error_msg)
            except (ValueError, KeyError, AttributeError):
                # JSON parsing failed or response structure unexpected
                pass
            get_logger().exception(f"C2B URL registration HTTP error: {error_msg}")
            return {"success": False, "message": error_msg}

        except requests.exceptions.RequestException as e:
            get_logger().exception(f"C2B URL registration request failed: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}

        except Exception as e:
            get_logger().exception(f"Unexpected error during C2B URL registration: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    def simulate_c2b_payment(
        self,
        phone: str,
        amount: float,
        bill_reference: str,
        command_id: str = "CustomerPayBillOnline",
    ) -> Dict[str, Any]:
        """
        Simulate a C2B payment (for testing in sandbox)
        
        Args:
            phone: Customer phone number
            amount: Payment amount
            bill_reference: Bill reference number
            command_id: Command ID (CustomerPayBillOnline or CustomerBuyGoodsOnline)
            
        Returns:
            Dictionary with simulation result
        """
        if not self.shortcode:
            return {
                "success": False,
                "message": "M-Pesa shortcode not configured",
            }

        # Format phone number
        phone_clean = "".join(filter(str.isdigit, phone))
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"
        elif not phone_clean.startswith("254"):
            phone_clean = f"254{phone_clean}"

        access_token = self.auth.get_access_token()
        if not access_token:
            return {
                "success": False,
                "message": "Failed to authenticate with M-Pesa API",
            }

        payload = {
            "ShortCode": self.shortcode,
            "CommandID": command_id,
            "Amount": int(amount),
            "Msisdn": phone_clean,
            "BillRefNumber": bill_reference,
        }

        url = f"{self.base_url}/mpesa/c2b/v1/simulate"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            get_logger().info(
                f"Simulating C2B payment: {phone_clean}, Amount: {amount}, Ref: {bill_reference}"
            )
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            response_code = data.get("ResponseCode")

            if response_code == "0":
                get_logger().info("C2B payment simulated successfully")
                return {
                    "success": True,
                    "response_code": response_code,
                    "response_description": data.get("ResponseDescription"),
                    "originator_conversation_id": data.get("OriginatorConversationID"),
                    "conversation_id": data.get("ConversationID"),
                }
            else:
                error_message = data.get("ResponseDescription", "Unknown error")
                get_logger().error(f"C2B simulation failed: {error_message}")
                return {
                    "success": False,
                    "message": error_message,
                    "response_code": response_code,
                }

        except Exception as e:
            get_logger().exception(f"C2B simulation failed: {e}")
            return {"success": False, "message": f"Simulation failed: {str(e)}"}

    @staticmethod
    def parse_validation_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse C2B validation callback payload from M-Pesa
        
        Args:
            payload: Raw callback payload from M-Pesa
            
        Returns:
            Parsed validation data
        """
        return {
            "transaction_type": payload.get("TransactionType"),
            "trans_id": payload.get("TransID"),
            "trans_time": payload.get("TransTime"),
            "trans_amount": payload.get("TransAmount"),
            "business_short_code": payload.get("BusinessShortCode"),
            "bill_ref_number": payload.get("BillRefNumber"),
            "invoice_number": payload.get("InvoiceNumber"),
            "org_account_balance": payload.get("OrgAccountBalance"),
            "third_party_trans_id": payload.get("ThirdPartyTransID"),
            "msisdn": payload.get("MSISDN"),
            "first_name": payload.get("FirstName"),
            "middle_name": payload.get("MiddleName"),
            "last_name": payload.get("LastName"),
        }

    @staticmethod
    def parse_confirmation_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse C2B confirmation callback payload from M-Pesa
        
        Args:
            payload: Raw callback payload from M-Pesa
            
        Returns:
            Parsed confirmation data
        """
        return {
            "transaction_type": payload.get("TransactionType"),
            "trans_id": payload.get("TransID"),
            "trans_time": payload.get("TransTime"),
            "trans_amount": payload.get("TransAmount"),
            "business_short_code": payload.get("BusinessShortCode"),
            "bill_ref_number": payload.get("BillRefNumber"),
            "invoice_number": payload.get("InvoiceNumber"),
            "org_account_balance": payload.get("OrgAccountBalance"),
            "third_party_trans_id": payload.get("ThirdPartyTransID"),
            "msisdn": payload.get("MSISDN"),
            "first_name": payload.get("FirstName"),
            "middle_name": payload.get("MiddleName"),
            "last_name": payload.get("LastName"),
        }

