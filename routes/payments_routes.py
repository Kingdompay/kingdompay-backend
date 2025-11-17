"""
Payment routes for Phase 2: external provider top-ups and payouts
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.provider_service import ProviderService
from services.ledger_service import LedgerService
from extensions import db
from models.payment import Payment
from models.wallet import Wallet
from models.ledger_journal import LedgerJournal
from decimal import Decimal


auth_service = AuthService()
provider_service = ProviderService()
ledger_service = LedgerService()


@api_v1_bp.route("/topups/momo", methods=["POST"])
@jwt_required()
def topup_via_momo():
    """Top-up wallet via mobile money (M-Pesa, Airtel, T-Kash)"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        wallet_id = data.get("wallet_id")
        amount = data.get("amount")
        phone = data.get("phone")
        provider = data.get("provider", "MPESA")

        if not wallet_id or not amount or not phone:
            return (
                jsonify({"success": False, "message": "wallet_id, amount, phone are required"}),
                400,
            )

        wallet = Wallet.query.get(wallet_id)
        if not wallet or wallet.user_id != user.id:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        adapter = provider_service.get_adapter(provider)
        if not adapter:
            return jsonify({"success": False, "message": "Provider not available"}), 400

        # Create pending payment record
        payment = Payment(
            payer_wallet_id=wallet_id,
            amount=Decimal(str(amount)),
            currency=wallet.currency,
            status="PENDING",
            method="MOMO",
            provider=provider.upper(),
        )
        db.session.add(payment)
        db.session.flush()

        # Initiate provider debit
        reference = f"TOPUP-{payment.id}"
        result = adapter.initiate_debit(
            phone=phone,
            amount=Decimal(str(amount)),
            currency=wallet.currency,
            reference=reference,
        )

        if result.success:
            payment.provider_ref = result.provider_ref
            db.session.commit()
            return jsonify({"success": True, "payment_id": payment.id, "status": "PENDING"}), 202
        else:
            payment.status = "FAILED"
            db.session.commit()
            return jsonify({"success": False, "message": result.message}), 400

    except Exception:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/webhooks/provider/<provider>", methods=["POST"])
def provider_webhook(provider: str):
    """Handle provider webhook callbacks"""
    try:
        adapter = provider_service.get_adapter(provider)
        if not adapter:
            current_app.logger.warning(f"Webhook received for unknown provider: {provider}")
            return jsonify({"success": False, "message": "Provider not found"}), 404

        payload = request.get_json() or request.form.to_dict()
        current_app.logger.info(f"Webhook received from {provider}: {payload}")
        
        event = adapter.handle_webhook(payload)
        current_app.logger.info(f"Webhook event parsed: {event}")

        provider_upper = provider.upper()
        status = event.get("status")

        # Find payment - try multiple methods for MPESA STK Push and B2C
        payment = None
        provider_ref = event.get("provider_ref")
        checkout_id = event.get("checkout_request_id")
        conversation_id = event.get("conversation_id")
        
        # For MPESA STK Push: payment is stored with CheckoutRequestID as provider_ref initially
        # Webhook returns MpesaReceiptNumber as provider_ref and CheckoutRequestID separately
        if checkout_id:
            # First try to find by checkout_request_id (most reliable for MPESA STK)
            payment = Payment.query.filter_by(
                provider=provider_upper, provider_ref=checkout_id
            ).first()
            current_app.logger.info(f"Payment lookup by checkout_id {checkout_id}: {payment.id if payment else 'not found'}")
        
        # For MPESA B2C: payment is stored with conversation_id as provider_ref initially
        if not payment and conversation_id:
            payment = Payment.query.filter_by(
                provider=provider_upper, provider_ref=conversation_id
            ).first()
            current_app.logger.info(f"Payment lookup by conversation_id {conversation_id}: {payment.id if payment else 'not found'}")
        
        if not payment and provider_ref:
            # Try to find by provider_ref (works for other providers or if receipt number matches)
            payment = Payment.query.filter_by(
                provider=provider_upper, provider_ref=provider_ref
            ).first()
            current_app.logger.info(f"Payment lookup by provider_ref {provider_ref}: {payment.id if payment else 'not found'}")
        
        if not payment:
            current_app.logger.warning(f"Payment not found for provider {provider_upper}, checkout_id: {checkout_id}, conversation_id: {conversation_id}, provider_ref: {provider_ref}")
            # Return 200 to prevent webhook retries for invalid requests
            return jsonify({"success": False, "message": "Payment not found"}), 200

        # Handle successful payment
        if status == "SUCCESS" and payment.status in ["PENDING", "PENDING_APPROVAL"]:
            # Update provider_ref to final receipt number if available (for MPESA STK or B2C)
            if provider_ref and provider_ref != checkout_id and provider_ref != conversation_id:
                payment.provider_ref = provider_ref
            
            # For payouts (payee_wallet_id), deduct from wallet
            # For top-ups (payer_wallet_id), credit to wallet
            if payment.payee_wallet_id:
                # This is a payout - deduct from wallet
                wallet = Wallet.query.get(payment.payee_wallet_id)
                if not wallet:
                    current_app.logger.error(f"Payment {payment.id}: Wallet {payment.payee_wallet_id} not found")
                    return jsonify({"success": False, "message": f"Wallet {payment.payee_wallet_id} not found"}), 400
                
                # Post ledger entry (debit from wallet)
                journal_result = ledger_service.post_transfer(
                    from_wallet_id=payment.payee_wallet_id,
                    to_wallet_id=None,  # External destination
                    amount=payment.amount,
                    currency=payment.currency,
                    memo="Payout via " + provider,
                    idempotency_key=f"provider-{payment.provider_ref or conversation_id or checkout_id}",
                    meta={"payment_id": payment.id, "provider": provider},
                )
            else:
                # This is a top-up - credit to wallet
                wallet = Wallet.query.get(payment.payer_wallet_id)
                if not wallet:
                    current_app.logger.error(f"Payment {payment.id}: Wallet {payment.payer_wallet_id} not found")
                    return jsonify({"success": False, "message": f"Wallet {payment.payer_wallet_id} not found"}), 400
                
                # Post ledger entry (credit to wallet)
                journal_result = ledger_service.post_transfer(
                    from_wallet_id=None,  # External source
                    to_wallet_id=payment.payer_wallet_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    memo="Top-up via " + provider,
                    idempotency_key=f"provider-{payment.provider_ref or checkout_id}",
                    meta={"payment_id": payment.id, "provider": provider},
                )
            
            if journal_result.get("success"):
                payment.status = "SUCCESS"
                payment.journal_id = journal_result.get("journal_id")
                db.session.commit()
                current_app.logger.info(f"Payment {payment.id} marked as SUCCESS")
                return jsonify({"success": True}), 200
            else:
                current_app.logger.error(f"Ledger posting failed for payment {payment.id}: {journal_result}")
                db.session.rollback()
                return jsonify({"success": False, "message": "Ledger posting failed"}), 500
        
        # Handle failed payment
        elif status == "FAILED" and payment.status == "PENDING":
            payment.status = "FAILED"
            db.session.commit()
            error_message = event.get("message", "Payment failed")
            current_app.logger.info(f"Payment {payment.id} marked as FAILED: {error_message}")
            return jsonify({"success": True}), 200

        # Payment already processed
        else:
            current_app.logger.info(f"Payment {payment.id} already in status {payment.status}, ignoring webhook")
            return jsonify({"success": True}), 200

    except Exception as e:
        current_app.logger.exception(f"Webhook processing failed for {provider}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Webhook processing failed"}), 500

