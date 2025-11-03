"""
Payment routes for Phase 2: external provider top-ups and payouts
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from api.v1 import api_v1_bp
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
            return jsonify({"success": False, "message": "Provider not found"}), 404

        payload = request.get_json() or request.form.to_dict()
        event = adapter.handle_webhook(payload)

        if event.get("status") == "SUCCESS":
            provider_ref = event.get("provider_ref")
            # Find payment by provider_ref
            payment = Payment.query.filter_by(
                provider=provider.upper(), provider_ref=provider_ref
            ).first()
            if not payment:
                # Try checkout_request_id for STK
                checkout_id = event.get("checkout_request_id")
                if checkout_id:
                    payment = Payment.query.filter_by(provider_ref=checkout_id).first()

            if payment and payment.status == "PENDING":
                # Post ledger entry
                journal_result = ledger_service.post_transfer(
                    from_wallet_id=None,  # External source
                    to_wallet_id=payment.payer_wallet_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    memo="Top-up via " + provider,
                    idempotency_key=f"provider-{provider_ref}",
                    meta={"payment_id": payment.id, "provider": provider},
                )
                if journal_result.get("success"):
                    payment.status = "SUCCESS"
                    payment.journal_id = journal_result.get("journal_id")
                    db.session.commit()
                    return jsonify({"success": True}), 200

        return jsonify({"success": False}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Webhook processing failed"}), 500

