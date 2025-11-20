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
        
        # M-Pesa STK Push limits
        self.MIN_AMOUNT = Decimal("1.00")  # Minimum 1 KES
        self.MAX_AMOUNT = Decimal("70000.00")  # Maximum 70,000 KES for STK Push

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
            
        Raises:
            ValueError: If phone number is invalid
        """
        if not phone:
            raise ValueError("Phone number cannot be empty")
        
        # Remove all non-digit characters
        phone_clean = "".join(filter(str.isdigit, phone))
        
        if not phone_clean:
            raise ValueError("Phone number must contain at least one digit")

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

        # Validate phone number length (should be 12 digits: 254 + 9 digits)
        if len(phone_clean) != 12:
            raise ValueError(f"Invalid phone number length: {len(phone_clean)} digits (expected 12)")
        
        # Validate it starts with 254
        if not phone_clean.startswith("254"):
            raise ValueError(f"Phone number must start with 254, got: {phone_clean}")

        return phone_clean
    
    def _validate_amount(self, amount: Decimal) -> Dict[str, Any]:
        """
        Validate amount against M-Pesa limits
        
        Args:
            amount: Payment amount
            
        Returns:
            Dict with validation result
        """
        if amount < self.MIN_AMOUNT:
            return {
                "valid": False,
                "message": f"Amount must be at least {self.MIN_AMOUNT} KES"
            }
        
        if amount > self.MAX_AMOUNT:
            return {
                "valid": False,
                "message": f"Amount cannot exceed {self.MAX_AMOUNT} KES for STK Push"
            }
        
        return {"valid": True}
    
    def _validate_callback_url(self, url: str) -> bool:
        """
        Validate callback URL format
        
        Args:
            url: Callback URL
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        # Must be HTTP or HTTPS
        if not (url.startswith("http://") or url.startswith("https://")):
            return False
        
        # For production, must be HTTPS
        if self.base_url == "https://api.safaricom.co.ke" and not url.startswith("https://"):
            return False
        
        return True

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
        missing_config = []
        if not self.shortcode:
            missing_config.append("MPESA_SHORTCODE")
        if not self.passkey:
            missing_config.append("MPESA_PASSKEY")
        if not self.callback_url:
            missing_config.append("MPESA_CALLBACK_URL")
        
        if missing_config:
            error_msg = f"M-Pesa STK Push not configured. Missing: {', '.join(missing_config)}"
            get_logger().error(error_msg)
            return {
                "success": False,
                "message": error_msg,
            }
        
        # Validate callback URL
        if not self._validate_callback_url(self.callback_url):
            error_msg = f"Invalid callback URL format: {self.callback_url}. Must be HTTPS for production."
            get_logger().error(error_msg)
            return {
                "success": False,
                "message": error_msg,
            }
        
        # Validate amount
        amount_validation = self._validate_amount(amount)
        if not amount_validation["valid"]:
            get_logger().error(f"Amount validation failed: {amount_validation['message']}")
            return {
                "success": False,
                "message": amount_validation["message"],
            }

        # Get access token
        access_token = self.auth.get_access_token()
        if not access_token:
            get_logger().error("Failed to authenticate with M-Pesa API")
            return {
                "success": False,
                "message": "Failed to authenticate with M-Pesa API",
            }

        # Format phone number
        try:
            phone_formatted = self._format_phone_number(phone)
        except ValueError as e:
            get_logger().error(f"Invalid phone number format: {phone} - {str(e)}")
            return {
                "success": False,
                "message": f"Invalid phone number format: {str(e)}",
            }
        except Exception as e:
            get_logger().exception(f"Unexpected error formatting phone number: {phone}")
            return {
                "success": False,
                "message": f"Invalid phone number format: {str(e)}",
            }

        # Validate account reference
        if not account_reference or len(account_reference.strip()) == 0:
            get_logger().error("Account reference is required")
            return {
                "success": False,
                "message": "Account reference is required",
            }

        # Generate password and timestamp
        password, timestamp = self._generate_password()
        
        # Validate shortcode format (should be string, not int)
        shortcode_str = str(self.shortcode).strip()

        # Prepare request payload
        # Ensure shortcode is string and amount is integer
        payload = {
            "BusinessShortCode": shortcode_str,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),  # M-Pesa requires integer amount
            "PartyA": phone_formatted,
            "PartyB": shortcode_str,
            "PhoneNumber": phone_formatted,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12].strip(),  # Max 12 characters, trimmed
            "TransactionDesc": (transaction_desc or "Payment")[:13].strip(),  # Max 13 characters, trimmed
        }
        
        # Log configuration (without sensitive data)
        get_logger().info(
            f"STK Push configuration: ShortCode={shortcode_str}, "
            f"BaseURL={self.base_url}, CallbackURL={self.callback_url[:50]}..."
        )

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
                    error_data = {"errorMessage": response.text, "raw_response": response.text[:500]}
                
                error_msg = error_data.get("errorMessage") or error_data.get("error_description") or error_data.get("error") or f"HTTP {response.status_code}"
                
                # Log full error details for debugging
                get_logger().error(
                    f"STK Push HTTP error {response.status_code}:\n"
                    f"  Error Message: {error_msg}\n"
                    f"  Full Response: {json.dumps(error_data, indent=2)}\n"
                    f"  Request Payload: {json.dumps(payload, indent=2)}"
                )
                
                return {
                    "success": False,
                    "message": f"M-Pesa API error: {response.status_code} - {error_msg}",
                    "response_code": str(response.status_code),
                    "error_details": error_data,
                    "debug_info": {
                        "shortcode": shortcode_str,
                        "phone": phone_formatted,
                        "amount": int(float(amount)),
                        "callback_url": self.callback_url,
                    }
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

