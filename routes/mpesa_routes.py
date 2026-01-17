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
    Initiate M-Pesa STK Push deposit
    ---
    tags:
      - M-Pesa
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - phone_number
            - amount
          properties:
            phone_number:
              type: string
              description: M-Pesa phone number (+254 or 07 format)
              example: "0712345678"
            amount:
              type: number
              minimum: 1
              maximum: 70000
              example: 1000
            reference:
              type: string
              description: Optional payment reference
              example: "Wallet top-up"
    responses:
      200:
        description: STK Push initiated - check your phone
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    
    try:
        data = request.get_json() or {}

        # Validate required fields - accept both 'phone' and 'phone_number' for flexibility
        phone = data.get("phone") or data.get("phone_number")
        amount = data.get("amount")
        account_reference = data.get("account_reference") or data.get("reference")
        transaction_desc = data.get("transaction_desc") or data.get("description", "Payment")

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


# ═══════════════════════════════════════════════════════════════════════════════
#                         M-PESA WITHDRAWAL (B2C)
# ═══════════════════════════════════════════════════════════════════════════════

@api_v1_bp.route("/mpesa/withdraw", methods=["POST"])
@jwt_required()
def initiate_withdrawal():
    """
    Initiate M-Pesa B2C withdrawal
    ---
    tags:
      - M-Pesa
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - phone_number
            - amount
          properties:
            phone_number:
              type: string
              description: M-Pesa phone number to receive funds
              example: "0712345678"
            amount:
              type: number
              minimum: 10
              maximum: 70000
              description: Amount in KES (min 10, max 70,000)
              example: 1000
    responses:
      200:
        description: Withdrawal initiated
        schema:
          type: object
          properties:
            success:
              type: boolean
            payment_id:
              type: integer
            transaction_id:
              type: integer
            amount:
              type: number
            phone:
              type: string
            new_balance:
              type: number
      400:
        description: Invalid request or insufficient balance
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Get phone number (accept both field names)
        phone = data.get("phone_number") or data.get("phone")
        amount = data.get("amount")
        
        # Validate required fields
        if not phone:
            return jsonify({
                "error": True,
                "message": "Phone number is required",
                "code": "MISSING_PHONE"
            }), 400
        
        if not amount:
            return jsonify({
                "error": True,
                "message": "Amount is required",
                "code": "MISSING_AMOUNT"
            }), 400
        
        # Parse and validate amount
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return jsonify({
                    "error": True,
                    "message": "Amount must be greater than zero",
                    "code": "INVALID_AMOUNT"
                }), 400
            if amount < 10:
                return jsonify({
                    "error": True,
                    "message": "Minimum withdrawal amount is 10 KES",
                    "code": "AMOUNT_TOO_LOW"
                }), 400
            if amount > 70000:
                return jsonify({
                    "error": True,
                    "message": "Maximum withdrawal amount is 70,000 KES",
                    "code": "AMOUNT_TOO_HIGH"
                }), 400
        except (InvalidOperation, ValueError):
            return jsonify({
                "error": True,
                "message": "Invalid amount format",
                "code": "INVALID_AMOUNT"
            }), 400
        
        # Validate phone number
        validated_phone = auth_service.validate_phone_number(phone)
        if not validated_phone:
            return jsonify({
                "error": True,
                "message": "Invalid phone number format. Use +254XXXXXXXXX or 07XXXXXXXX",
                "code": "INVALID_PHONE"
            }), 400
        
        # Get user's wallet
        wallet = Wallet.query.filter_by(user_id=int(user_id)).first()
        if not wallet:
            return jsonify({
                "error": True,
                "message": "Wallet not found",
                "code": "WALLET_NOT_FOUND"
            }), 404
        
        # Check sufficient balance
        if wallet.balance < amount:
            return jsonify({
                "error": True,
                "message": f"Insufficient balance. Available: {wallet.balance} KES",
                "code": "INSUFFICIENT_BALANCE"
            }), 400
        
        # Deduct from wallet (will be refunded if B2C fails)
        wallet.balance -= amount
        
        # Create withdrawal transaction
        from models.transaction import Transaction
        
        withdrawal_txn = Transaction(
            source_wallet_id=wallet.id,
            transaction_type="WITHDRAWAL",
            amount=amount,
            source_balance_after=wallet.balance,
            description=f"M-Pesa withdrawal to {validated_phone}",
            status="PENDING",
        )
        db.session.add(withdrawal_txn)
        db.session.flush()  # Get transaction ID
        
        # Create payment record
        payment = Payment(
            method="MOMO",
            amount=amount,
            currency="KES",
            status="PENDING",
            provider="MPESA",
            payer_wallet_id=wallet.id,
            payer_phone=validated_phone
        )
        db.session.add(payment)
        db.session.flush()
        
        # Update transaction with payment reference
        withdrawal_txn.reference_number = f"WDR-{payment.id}"
        
        # Initiate B2C payout
        result = b2c_service.initiate_payout(
            phone=validated_phone,
            amount=amount,
            remarks=f"KingdomPay Withdrawal #{payment.id}",
            occasion="Withdrawal"
        )
        
        if result.get("success"):
            # Store conversation ID for callback matching
            payment.provider_ref = result.get("conversation_id")
            db.session.commit()
            
            current_app.logger.info(
                f"Withdrawal initiated: User {user_id}, Amount {amount}, "
                f"Phone {validated_phone}, ConversationID {result.get('conversation_id')}"
            )
            
            return jsonify({
                "success": True,
                "message": "Withdrawal initiated. You will receive the money shortly.",
                "payment_id": payment.id,
                "transaction_id": withdrawal_txn.id,
                "amount": float(amount),
                "phone": validated_phone,
                "conversation_id": result.get("conversation_id"),
                "new_balance": float(wallet.balance)
            }), 200
        else:
            # B2C initiation failed - refund wallet
            wallet.balance += amount
            withdrawal_txn.status = "FAILED"
            withdrawal_txn.description += f" - Failed: {result.get('message')}"
            payment.status = "FAILED"
            payment.failure_reason = result.get("message")
            db.session.commit()
            
            current_app.logger.error(
                f"Withdrawal failed for user {user_id}: {result.get('message')}"
            )
            
            return jsonify({
                "error": True,
                "message": result.get("message", "Withdrawal initiation failed"),
                "code": "WITHDRAWAL_FAILED"
            }), 400
            
    except Exception as e:
        current_app.logger.exception("Error initiating withdrawal")
        db.session.rollback()
        return jsonify({
            "error": True,
            "message": "An unexpected error occurred",
            "code": "INTERNAL_ERROR"
        }), 500


@api_v1_bp.route("/mpesa/callback", methods=["POST"])
def handle_stk_callback():
    """
    Handle STK Push callback from M-Pesa
    POST /api/v1/mpesa/callback

    This endpoint receives callbacks from M-Pesa when a customer
    completes or cancels an STK Push payment.
    
    On successful payment:
    1. Updates Payment record status to SUCCESS
    2. Credits user's wallet with the deposited amount
    3. Creates a transaction record
    """
    try:
        payload = request.get_json() or {}
        current_app.logger.info(f"M-Pesa STK callback received: {payload}")

        # Extract callback data
        body = payload.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        checkout_request_id = stk_callback.get("CheckoutRequestID")

        if not stk_callback:
            current_app.logger.warning(
                "Invalid STK callback format: missing stkCallback"
            )
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        merchant_request_id = stk_callback.get("MerchantRequestID")

        current_app.logger.info(
            f"STK Callback - CheckoutRequestID: {checkout_request_id}, "
            f"ResultCode: {result_code}, ResultDesc: {result_desc}"
        )

        # Find the payment by checkout_request_id (stored as provider_ref)
        payment = Payment.query.filter_by(provider_ref=checkout_request_id).first()
        
        if not payment:
            current_app.logger.warning(f"Payment not found for CheckoutRequestID: {checkout_request_id}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Payment not found"}), 200

        # Process successful payment
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

            # Update payment status
            payment.status = "SUCCESS"
            payment.provider_transaction_id = receipt_number
            
            # Credit user's wallet if payment has a wallet association
            if payment.payer_wallet_id:
                wallet = Wallet.query.get(payment.payer_wallet_id)
                if wallet:
                    # Credit the wallet
                    from models.transaction import Transaction
                    
                    deposit_amount = Decimal(str(amount))
                    wallet.balance += deposit_amount
                    
                    # Create transaction record
                    transaction = Transaction(
                        destination_wallet_id=wallet.id,
                        transaction_type="DEPOSIT",
                        amount=deposit_amount,
                        destination_balance_after=wallet.balance,
                        description=f"M-Pesa deposit - Receipt: {receipt_number}",
                        reference_number=receipt_number,
                        status="SUCCESS",
                    )
                    db.session.add(transaction)
                    
                    current_app.logger.info(
                        f"Wallet {wallet.id} credited with {amount} KES. "
                        f"New balance: {wallet.balance}"
                    )
            else:
                # Payment doesn't have wallet - try to find user by phone
                phone_formatted = f"+{phone}" if phone and not phone.startswith("+") else phone
                from models.user import User
                user = User.query.filter_by(phone_number=phone_formatted).first()
                
                if user:
                    wallet = Wallet.find_by_user_id(user.id)
                    if wallet:
                        from models.transaction import Transaction
                        
                        deposit_amount = Decimal(str(amount))
                        wallet.balance += deposit_amount
                        
                        transaction = Transaction(
                            destination_wallet_id=wallet.id,
                            transaction_type="DEPOSIT",
                            amount=deposit_amount,
                            destination_balance_after=wallet.balance,
                            description=f"M-Pesa deposit - Receipt: {receipt_number}",
                            reference_number=receipt_number,
                            status="SUCCESS",
                        )
                        db.session.add(transaction)
                        
                        # Update payment with wallet
                        payment.payer_wallet_id = wallet.id
                        
                        current_app.logger.info(
                            f"Wallet {wallet.id} (user: {user.id}) credited with {amount} KES"
                        )

            db.session.commit()
            
        else:
            # Payment failed or cancelled
            payment.status = "FAILED"
            payment.failure_reason = result_desc
            db.session.commit()
            
            current_app.logger.warning(
                f"STK Push failed/cancelled: {result_desc}"
            )

        return (
            jsonify({"ResultCode": 0, "ResultDesc": "Callback processed successfully"}),
            200,
        )

    except Exception as e:
        current_app.logger.exception("Error processing STK callback")
        db.session.rollback()
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
    
    On successful payout:
    - Updates Payment record status to SUCCESS
    - Transaction was already deducted from wallet at initiation
    
    On failed payout:
    - Updates Payment record status to FAILED
    - Refunds the amount back to user's wallet
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
        originator_conversation_id = result_data.get("originator_conversation_id")

        current_app.logger.info(
            f"B2C Result - ResultCode: {result_code}, "
            f"TransactionID: {transaction_id}, Receipt: {transaction_receipt}, "
            f"Amount: {transaction_amount}, ConversationID: {conversation_id}"
        )

        # Find the payment by conversation_id
        payment = Payment.query.filter_by(provider_ref=conversation_id).first()
        if not payment:
            # Try originator_conversation_id
            payment = Payment.query.filter_by(provider_ref=originator_conversation_id).first()
        
        if not payment:
            current_app.logger.warning(f"Payment not found for ConversationID: {conversation_id}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Payment not found"}), 200

        if result_code == 0:
            # B2C payout successful
            payment.status = "SUCCESS"
            payment.provider_transaction_id = transaction_receipt or transaction_id
            db.session.commit()
            
            current_app.logger.info(
                f"B2C payout successful - Receipt: {transaction_receipt}, "
                f"Amount: {transaction_amount}"
            )
        else:
            # B2C payout failed - refund the wallet
            payment.status = "FAILED"
            payment.failure_reason = result_data.get("result_desc", "Payout failed")
            
            # Refund to wallet
            if payment.payer_wallet_id:
                wallet = Wallet.query.get(payment.payer_wallet_id)
                if wallet:
                    from models.transaction import Transaction
                    
                    refund_amount = payment.amount
                    wallet.balance += refund_amount
                    
                    # Create refund transaction
                    refund_txn = Transaction(
                        destination_wallet_id=wallet.id,
                        transaction_type="REFUND",
                        amount=refund_amount,
                        destination_balance_after=wallet.balance,
                        description=f"Refund: Withdrawal failed - {payment.failure_reason}",
                        reference_number=f"REF-{payment.id}",
                        status="SUCCESS",
                    )
                    db.session.add(refund_txn)
                    
                    current_app.logger.info(
                        f"Wallet {wallet.id} refunded {refund_amount} KES due to failed B2C"
                    )
            
            db.session.commit()
            
            current_app.logger.warning(
                f"B2C payout failed: {result_data.get('result_desc')}"
            )

        return jsonify({"ResultCode": 0, "ResultDesc": "Result processed successfully"}), 200

    except Exception as e:
        current_app.logger.exception("Error processing B2C result")
        db.session.rollback()
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
