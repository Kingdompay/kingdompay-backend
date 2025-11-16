"""
M-Pesa STK Push (Lipa na M-Pesa Online)
Handles STK Push payment initiation
"""

import os
import json
import base64
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from .auth import MpesaAuth, get_logger


class MpesaSTKPush:
    """Handles M-Pesa STK Push (Lipa na M-Pesa Online) payments"""

    def __init__(self):
        self.auth = MpesaAuth()
        self.base_url = os.environ.get(
            "MPESA_BASE_URL", "https://sandbox.safaricom.co.ke"
        )
        self.shortcode = os.environ.get("MPESA_SHORTCODE")
        self.passkey = os.environ.get("MPESA_PASSKEY")
        self.callback_url = os.environ.get("MPESA_CALLBACK_URL")

    def _generate_password(self) -> Tuple[str, str]:
        """
        Generate M-Pesa API password using shortcode, passkey, and timestamp
        
        Returns:
            Tuple of (password, timestamp) where password is base64 encoded
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(data_to_encode.encode()).decode()
        return password, timestamp

    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number to M-Pesa format (254XXXXXXXXX)
        
        Args:
            phone: Phone number in any format
            
        Returns:
            Formatted phone number
        """
        # Remove all non-digit characters
        phone_clean = "".join(filter(str.isdigit, phone))

        # Convert to 254 format
        if phone_clean.startswith("0"):
            phone_clean = f"254{phone_clean[1:]}"
        elif phone_clean.startswith("254"):
            pass  # Already in correct format
        elif phone_clean.startswith("+254"):
            phone_clean = phone_clean[1:]
        else:
            # Assume it's missing country code
            phone_clean = f"254{phone_clean}"

        return phone_clean

    def initiate_stk_push(
        self,
        phone: str,
        amount: Decimal,
        account_reference: str,
        transaction_desc: str = "Payment",
    ) -> Dict[str, Any]:
        """
        Initiate STK Push payment request
        
        Args:
            phone: Customer phone number
            amount: Payment amount
            account_reference: Unique reference for the transaction
            transaction_desc: Transaction description
            
        Returns:
            Dictionary with success status and response data
        """
        # Validate configuration
        if not all([self.shortcode, self.passkey, self.callback_url]):
            return {
                "success": False,
                "message": "M-Pesa STK Push not configured. Missing SHORTCODE, PASSKEY, or CALLBACK_URL",
            }

        # Get access token
        access_token = self.auth.get_access_token()
        if not access_token:
            return {
                "success": False,
                "message": "Failed to authenticate with M-Pesa API",
            }

        # Format phone number
        try:
            phone_formatted = self._format_phone_number(phone)
        except Exception as e:
            get_logger().error(f"Invalid phone number format: {phone}")
            return {
                "success": False,
                "message": f"Invalid phone number format: {str(e)}",
            }

        # Generate password and timestamp
        password, timestamp = self._generate_password()

        # Prepare request payload
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": phone_formatted,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_formatted,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],  # Max 12 characters
            "TransactionDesc": transaction_desc[:13],  # Max 13 characters
        }

        # Make API request
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            get_logger().info(
                f"Initiating STK Push: {phone_formatted}, Amount: {amount}, Ref: {account_reference}"
            )
            get_logger().debug(f"STK Push payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response for debugging
            get_logger().debug(f"STK Push response status: {response.status_code}")
            get_logger().debug(f"STK Push response: {response.text}")

            # Check HTTP status
            if response.status_code != 200:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    error_data = {"errorMessage": response.text}
                
                error_msg = error_data.get("errorMessage") or error_data.get("error_description") or f"HTTP {response.status_code}"
                get_logger().error(f"STK Push HTTP error {response.status_code}: {error_msg}")
                return {
                    "success": False,
                    "message": f"M-Pesa API error: {response.status_code} - {error_msg}",
                    "response_code": str(response.status_code),
                    "error_details": error_data
                }

            data = response.json()

            # Check response
            response_code = data.get("ResponseCode")
            if response_code == "0":
                checkout_request_id = data.get("CheckoutRequestID")
                customer_message = data.get("CustomerMessage")
                get_logger().info(
                    f"STK Push initiated successfully. CheckoutRequestID: {checkout_request_id}"
                )
                return {
                    "success": True,
                    "checkout_request_id": checkout_request_id,
                    "customer_message": customer_message,
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "response_code": response_code,
                }
            else:
                error_message = data.get("ResponseDescription", "Unknown error")
                get_logger().error(
                    f"STK Push failed: {error_message} (Code: {response_code})"
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
                error_msg = error_data.get("errorMessage") or error_data.get("error_description") or error_msg
                get_logger().error(f"STK Push HTTP error: {error_msg}")
                get_logger().error(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                get_logger().error(f"STK Push HTTP error: {error_msg}")
            return {"success": False, "message": f"M-Pesa API error: {e.response.status_code} - {error_msg}"}

        except requests.exceptions.RequestException as e:
            get_logger().exception(f"STK Push request failed: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}

        except Exception as e:
            get_logger().exception(f"Unexpected error during STK Push: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    def query_stk_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Query STK Push transaction status
        
        Args:
            checkout_request_id: The CheckoutRequestID from initiate_stk_push
            
        Returns:
            Dictionary with transaction status
        """
        access_token = self.auth.get_access_token()
        if not access_token:
            return {
                "success": False,
                "message": "Failed to authenticate with M-Pesa API",
            }

        password, timestamp = self._generate_password()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            result_code = data.get("ResultCode")
            result_desc = data.get("ResultDesc")

            return {
                "success": result_code == "0",
                "result_code": result_code,
                "result_desc": result_desc,
                "checkout_request_id": checkout_request_id,
            }

        except Exception as e:
            get_logger().exception(f"STK status query failed: {e}")
            return {"success": False, "message": f"Query failed: {str(e)}"}

