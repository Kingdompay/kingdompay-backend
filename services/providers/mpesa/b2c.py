"""
M-Pesa B2C (Business to Customer) API
Handles B2C payouts to customers
"""

import os
import json
import requests
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from .auth import MpesaAuth, get_logger


class MpesaB2C:
    """Handles M-Pesa B2C (Business to Customer) payouts"""

    def __init__(self):
        self.auth = MpesaAuth()
        self.base_url = os.environ.get(
            "MPESA_BASE_URL", "https://sandbox.safaricom.co.ke"
        )
        self.shortcode = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name = os.environ.get("MPESA_INITIATOR_NAME")
        self.security_credential = os.environ.get("MPESA_SECURITY_CREDENTIAL")
        self.queue_timeout_url = os.environ.get(
            "MPESA_B2C_QUEUE_TIMEOUT_URL",
            os.environ.get("MPESA_CALLBACK_URL", "").replace("/callback", "/b2c/queue-timeout")
        )
        self.result_url = os.environ.get(
            "MPESA_B2C_RESULT_URL",
            os.environ.get("MPESA_CALLBACK_URL", "").replace("/callback", "/b2c/result")
        )

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

    def initiate_payout(
        self,
        phone: str,
        amount: Decimal,
        remarks: str = "Payout",
        occasion: Optional[str] = None,
        command_id: str = "BusinessPayment",
    ) -> Dict[str, Any]:
        """
        Initiate B2C payout to customer
        
        Args:
            phone: Recipient phone number
            amount: Payout amount
            remarks: Transaction remarks (max 100 characters)
            occasion: Optional occasion (max 100 characters)
            command_id: Command ID - "SalaryPayment", "BusinessPayment", or "PromotionPayment"
            
        Returns:
            Dictionary with success status and response data
        """
        # Validate configuration
        if not all([self.shortcode, self.initiator_name, self.security_credential]):
            missing = []
            if not self.shortcode:
                missing.append("MPESA_SHORTCODE")
            if not self.initiator_name:
                missing.append("MPESA_INITIATOR_NAME")
            if not self.security_credential:
                missing.append("MPESA_SECURITY_CREDENTIAL")
            
            return {
                "success": False,
                "message": f"M-Pesa B2C not configured. Missing: {', '.join(missing)}",
            }

        if not self.queue_timeout_url or not self.result_url:
            return {
                "success": False,
                "message": "B2C callback URLs not configured. Set MPESA_B2C_QUEUE_TIMEOUT_URL and MPESA_B2C_RESULT_URL",
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

        # Validate command ID
        valid_commands = ["SalaryPayment", "BusinessPayment", "PromotionPayment"]
        if command_id not in valid_commands:
            return {
                "success": False,
                "message": f"Invalid command_id. Must be one of: {', '.join(valid_commands)}",
            }

        # Truncate remarks and occasion to max length
        remarks = remarks[:100] if remarks else "Payout"
        occasion = occasion[:100] if occasion else None

        # Prepare request payload
        payload = {
            "InitiatorName": self.initiator_name,
            "SecurityCredential": self.security_credential,
            "CommandID": command_id,
            "Amount": int(float(amount)),
            "PartyA": self.shortcode,
            "PartyB": phone_formatted,
            "Remarks": remarks,
            "QueueTimeOutURL": self.queue_timeout_url,
            "ResultURL": self.result_url,
        }

        # Add occasion if provided
        if occasion:
            payload["Occasion"] = occasion

        # Make API request
        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            get_logger().info(
                f"Initiating B2C payout: {phone_formatted}, Amount: {amount}, Command: {command_id}"
            )
            get_logger().debug(f"B2C payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response for debugging
            get_logger().debug(f"B2C response status: {response.status_code}")
            get_logger().debug(f"B2C response: {response.text}")

            # Check HTTP status
            if response.status_code != 200:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    error_data = {"errorMessage": response.text}
                
                error_msg = error_data.get("errorMessage") or error_data.get("error_description") or f"HTTP {response.status_code}"
                get_logger().error(f"B2C HTTP error {response.status_code}: {error_msg}")
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
                originator_conversation_id = data.get("OriginatorConversationID")
                conversation_id = data.get("ConversationID")
                get_logger().info(
                    f"B2C payout initiated successfully. ConversationID: {conversation_id}"
                )
                return {
                    "success": True,
                    "originator_conversation_id": originator_conversation_id,
                    "conversation_id": conversation_id,
                    "response_code": response_code,
                    "response_description": data.get("ResponseDescription"),
                }
            else:
                error_message = data.get("ResponseDescription", "Unknown error")
                get_logger().error(
                    f"B2C payout failed: {error_message} (Code: {response_code})"
                )
                return {
                    "success": False,
                    "message": error_message,
                    "response_code": response_code,
                    "originator_conversation_id": data.get("OriginatorConversationID"),
                    "conversation_id": data.get("ConversationID"),
                }

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("errorMessage") or error_data.get("error_description") or error_msg
                get_logger().error(f"B2C HTTP error: {error_msg}")
                get_logger().error(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                get_logger().error(f"B2C HTTP error: {error_msg}")
            return {"success": False, "message": f"M-Pesa API error: {e.response.status_code} - {error_msg}"}

        except requests.exceptions.RequestException as e:
            get_logger().exception(f"B2C request failed: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}

        except Exception as e:
            get_logger().exception(f"Unexpected error during B2C payout: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    @staticmethod
    def parse_result_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse B2C result callback payload from M-Pesa
        
        Args:
            payload: Raw callback payload from M-Pesa
            
        Returns:
            Parsed result data
        """
        result = payload.get("Result", {})
        result_parameters = result.get("ResultParameters", {})
        result_parameter = result_parameters.get("ResultParameter", [])
        
        # Extract transaction details
        transaction_details = {}
        for param in result_parameter:
            key = param.get("Key")
            value = param.get("Value")
            if key:
                transaction_details[key] = value
        
        return {
            "result_type": result.get("ResultType"),
            "result_code": result.get("ResultCode"),
            "result_desc": result.get("ResultDesc"),
            "originator_conversation_id": result.get("OriginatorConversationID"),
            "conversation_id": result.get("ConversationID"),
            "transaction_id": result.get("TransactionID"),
            "transaction_amount": transaction_details.get("TransactionAmount"),
            "transaction_receipt": transaction_details.get("TransactionReceipt"),
            "b2c_recipient_is_registered_customer": transaction_details.get("B2CRecipientIsRegisteredCustomer"),
            "b2c_charges_paid_account_available_funds": transaction_details.get("B2CChargesPaidAccountAvailableFunds"),
            "receiver_public_name": transaction_details.get("ReceiverPartyPublicName"),
            "transaction_completed_date_time": transaction_details.get("TransactionCompletedDateTime"),
            "b2c_utility_account_available_funds": transaction_details.get("B2CUtilityAccountAvailableFunds"),
            "b2c_working_account_available_funds": transaction_details.get("B2CWorkingAccountAvailableFunds"),
        }

    @staticmethod
    def parse_queue_timeout_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse B2C queue timeout callback payload from M-Pesa
        
        Args:
            payload: Raw callback payload from M-Pesa
            
        Returns:
            Parsed timeout data
        """
        return {
            "result_type": payload.get("ResultType"),
            "result_code": payload.get("ResultCode"),
            "result_desc": payload.get("ResultDesc"),
            "originator_conversation_id": payload.get("OriginatorConversationID"),
            "conversation_id": payload.get("ConversationID"),
            "transaction_id": payload.get("TransactionID"),
        }

