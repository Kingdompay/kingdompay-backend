"""
M-Pesa payment routes
Handles STK Push and C2B payment endpoints
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from routes import api_v1_bp
from services.providers.mpesa.stk_push import MpesaSTKPush
from services.providers.mpesa.c2b import MpesaC2B
from services.providers.mpesa.b2c import MpesaB2C
from services.auth_service import AuthService
from extensions import db
from models.payment import Payment
from models.wallet import Wallet
from decimal import Decimal, InvalidOperation


stk_push_service = MpesaSTKPush()
c2b_service = MpesaC2B()
b2c_service = MpesaB2C()
auth_service = AuthService()


@api_v1_bp.route("/mpesa/status", methods=["GET"])
def mpesa_status():
    """Check M-Pesa integration status"""
    return jsonify({
        "success": True,
        "message": "M-Pesa routes are active",
        "endpoints": {
            "stk_push": "/api/v1/mpesa/pay",
            "callback": "/api/v1/mpesa/callback"
        }
    }), 200


@api_v1_bp.route("/mpesa/pay", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def initiate_stk_push():
    """
    Initiate STK Push payment
    POST /api/v1/mpesa/pay

    Request body:
    {
        "phone": "254712345678",
        "amount": 100.00,
        "account_reference": "PAY-12345",
        "transaction_desc": "Payment for services" (optional)
    }

    Returns:
    {
        "success": true,
        "checkout_request_id": "ws_CO_123456789",
        "customer_message": "Success. Request accepted for processing",
        "merchant_request_id": "12345-67890-1"
    }
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    
    try:
        data = request.get_json() or {}

        # Validate required fields
        phone = data.get("phone")
        amount = data.get("amount")
        account_reference = data.get("account_reference")
        transaction_desc = data.get("transaction_desc", "Payment")

        if not phone:
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Phone number is required",
                        "code": "MISSING_PHONE",
                    }
                ),
                400,
            )

        if not amount:
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Amount is required",
                        "code": "MISSING_AMOUNT",
                    }
                ),
                400,
            )

        if not account_reference:
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Account reference is required",
                        "code": "MISSING_REFERENCE",
                    }
                ),
                400,
            )

        # Validate and convert amount
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return (
                    jsonify(
                        {
                            "error": True,
                            "message": "Amount must be greater than 0",
                            "code": "INVALID_AMOUNT",
                        }
                    ),
                    400,
                )
        except (InvalidOperation, ValueError):
            return (
                jsonify(
                    {
                        "error": True,
                        "message": "Invalid amount format",
                        "code": "INVALID_AMOUNT",
                    }
                ),
                400,
            )

        # Try to get user and wallet if authenticated
        user = None
        wallet_id = None
        try:
            user = auth_service.get_current_user()
            if user:
                wallet = Wallet.find_by_user_id(user.id)
                if wallet:
                    wallet_id = wallet.id
        except:
            # User not authenticated or wallet not found - continue without wallet
            pass

        # Create Payment record before initiating STK Push
        # This ensures webhook handler can find the payment
        payment = Payment(
            payer_wallet_id=wallet_id,  # May be None if user not authenticated
            amount=amount_decimal,
            currency="KES",  # M-Pesa only supports KES
            status="PENDING",
            method="MOMO",
            provider="MPESA",
        )
        db.session.add(payment)
        db.session.flush()  # Get payment.id before commit

        # Use payment ID in account reference if not provided
        if not account_reference:
            account_reference = f"PAY-{payment.id}"

        # Initiate STK Push
        result = stk_push_service.initiate_stk_push(
            phone=phone,
            amount=amount_decimal,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
        )

        if result.get("success"):
            # Update payment with checkout_request_id as provider_ref
            checkout_request_id = result.get("checkout_request_id")
            payment.provider_ref = checkout_request_id
            db.session.commit()

            return (
                jsonify(
                    {
                        "success": True,
                        "payment_id": payment.id,
                        "checkout_request_id": checkout_request_id,
                        "customer_message": result.get("customer_message"),
                        "merchant_request_id": result.get("merchant_request_id"),
                        "response_code": result.get("response_code"),
                    }
                ),
                200,
            )
        else:
            # STK Push failed - mark payment as failed
            payment.status = "FAILED"
            db.session.commit()

            error_response = {
                "error": True,
                "message": result.get("message", "STK Push initiation failed"),
                "code": "STK_PUSH_FAILED",
                "response_code": result.get("response_code"),
                "payment_id": payment.id,  # Include payment ID even on failure
            }
            # Include error details if available for debugging
            if result.get("error_details"):
                error_response["error_details"] = result.get("error_details")
            return jsonify(error_response), 400

    except Exception as e:
        current_app.logger.exception("Error initiating STK Push")
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": True,
                    "message": "An unexpected error occurred",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


@api_v1_bp.route("/mpesa/callback", methods=["POST"])
def handle_stk_callback():
    """
    Handle STK Push callback from M-Pesa
    POST /api/v1/mpesa/callback

    This endpoint receives callbacks from M-Pesa when a customer
    completes or cancels an STK Push payment.
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa STK callback received: {payload}")

        # Extract callback data
        body = payload.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        checkout_request_id = body.get("CheckoutRequestID")

        if not stk_callback:
            current_app.logger.warning(
                "Invalid STK callback format: missing stkCallback"
            )
            # Return 200 to prevent M-Pesa from retrying
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        merchant_request_id = stk_callback.get("MerchantRequestID")

        # Log callback details
        current_app.logger.info(
            f"STK Callback - CheckoutRequestID: {checkout_request_id}, "
            f"ResultCode: {result_code}, ResultDesc: {result_desc}"
        )

        # Extract transaction details if successful
        if result_code == 0:
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            items = callback_metadata.get("Item", [])

            receipt_number = None
            amount = None
            phone = None
            transaction_date = None

            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                if name == "MpesaReceiptNumber":
                    receipt_number = value
                elif name == "Amount":
                    amount = value
                elif name == "PhoneNumber":
                    phone = value
                elif name == "TransactionDate":
                    transaction_date = value

            current_app.logger.info(
                f"STK Push successful - Receipt: {receipt_number}, "
                f"Amount: {amount}, Phone: {phone}"
            )

        # Always return success to M-Pesa to acknowledge receipt
        # Actual payment processing should be handled by webhook service
        return (
            jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"}),
            200,
        )

    except Exception as e:
        current_app.logger.exception("Error processing STK callback")
        # Still return success to prevent retries
        return jsonify({"ResultCode": 0, "ResultDesc": "Callback received"}), 200


@api_v1_bp.route("/payments/c2b/confirmation", methods=["POST"])
def handle_c2b_confirmation():
    """
    Handle C2B confirmation callback from M-Pesa
    POST /api/v1/payments/c2b/confirmation

    This endpoint receives confirmation callbacks from M-Pesa when
    a C2B payment is completed.
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa C2B confirmation received: {payload}")

        # Parse confirmation data
        confirmation_data = c2b_service.parse_confirmation_callback(payload)

        trans_id = confirmation_data.get("trans_id")
        trans_amount = confirmation_data.get("trans_amount")
        msisdn = confirmation_data.get("msisdn")
        bill_ref = confirmation_data.get("bill_ref_number")

        current_app.logger.info(
            f"C2B Confirmation - TransID: {trans_id}, "
            f"Amount: {trans_amount}, MSISDN: {msisdn}, BillRef: {bill_ref}"
        )

        # Process the confirmation (e.g., update payment status, credit wallet)
        # This should integrate with your payment processing logic

        # Return success to M-Pesa
        return (
            jsonify(
                {"ResultCode": 0, "ResultDesc": "Confirmation received successfully"}
            ),
            200,
        )

    except Exception as e:
        current_app.logger.exception("Error processing C2B confirmation")
        return jsonify({"ResultCode": 0, "ResultDesc": "Confirmation received"}), 200


@api_v1_bp.route("/payments/c2b/validation", methods=["POST"])
def handle_c2b_validation():
    """
    Handle C2B validation callback from M-Pesa
    POST /api/v1/payments/c2b/validation

    This endpoint receives validation callbacks from M-Pesa before
    processing a C2B payment. You can validate the transaction here.
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa C2B validation received: {payload}")

        # Parse validation data
        validation_data = c2b_service.parse_validation_callback(payload)

        trans_id = validation_data.get("trans_id")
        trans_amount = validation_data.get("trans_amount")
        msisdn = validation_data.get("msisdn")
        bill_ref = validation_data.get("bill_ref_number")

        current_app.logger.info(
            f"C2B Validation - TransID: {trans_id}, "
            f"Amount: {trans_amount}, MSISDN: {msisdn}, BillRef: {bill_ref}"
        )

        # Validate the transaction
        # Return ResultCode 0 to accept, or non-zero to reject
        # For now, accept all validations
        validation_result = {"ResultCode": 0, "ResultDesc": "Accepted"}

        # You can add custom validation logic here:
        # - Check if bill_ref exists in your system
        # - Validate amount
        # - Check customer account status
        # etc.

        return jsonify(validation_result), 200

    except Exception as e:
        current_app.logger.exception("Error processing C2B validation")
        # Reject on error to be safe
        return jsonify({"ResultCode": 1, "ResultDesc": "Validation error"}), 200


@api_v1_bp.route("/mpesa/b2c/result", methods=["POST"])
def handle_b2c_result():
    """
    Handle B2C result callback from M-Pesa
    POST /api/v1/mpesa/b2c/result

    This endpoint receives result callbacks from M-Pesa when
    a B2C payout is completed.
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa B2C result received: {payload}")

        # Parse result data
        result_data = b2c_service.parse_result_callback(payload)

        result_code = result_data.get("result_code")
        transaction_id = result_data.get("transaction_id")
        transaction_receipt = result_data.get("transaction_receipt")
        transaction_amount = result_data.get("transaction_amount")
        conversation_id = result_data.get("conversation_id")

        current_app.logger.info(
            f"B2C Result - ResultCode: {result_code}, "
            f"TransactionID: {transaction_id}, Receipt: {transaction_receipt}, "
            f"Amount: {transaction_amount}, ConversationID: {conversation_id}"
        )

        # The webhook handler at /api/v1/webhooks/provider/MPESA will process this
        # We just acknowledge receipt here
        return jsonify({"ResultCode": 0, "ResultDesc": "Result received successfully"}), 200

    except Exception as e:
        current_app.logger.exception("Error processing B2C result")
        # Still return success to prevent retries
        return jsonify({"ResultCode": 0, "ResultDesc": "Result received"}), 200


@api_v1_bp.route("/mpesa/b2c/queue-timeout", methods=["POST"])
def handle_b2c_queue_timeout():
    """
    Handle B2C queue timeout callback from M-Pesa
    POST /api/v1/mpesa/b2c/queue-timeout

    This endpoint receives timeout callbacks from M-Pesa when
    a B2C payout request times out in the queue.
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa B2C queue timeout received: {payload}")

        # Parse timeout data
        timeout_data = b2c_service.parse_queue_timeout_callback(payload)

        result_code = timeout_data.get("result_code")
        transaction_id = timeout_data.get("transaction_id")
        conversation_id = timeout_data.get("conversation_id")

        current_app.logger.warning(
            f"B2C Queue Timeout - ResultCode: {result_code}, "
            f"TransactionID: {transaction_id}, ConversationID: {conversation_id}"
        )

        # Acknowledge receipt
        return jsonify({"ResultCode": 0, "ResultDesc": "Timeout received"}), 200

    except Exception as e:
        current_app.logger.exception("Error processing B2C queue timeout")
        return jsonify({"ResultCode": 0, "ResultDesc": "Timeout received"}), 200
