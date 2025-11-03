"""
Hosted Checkout routes for Phase 2
"""

import uuid
import qrcode
import io
import base64
from flask import request, jsonify, render_template, url_for
from api.v1 import api_v1_bp
from services.provider_service import ProviderService
from services.ledger_service import LedgerService
from extensions import db
from models.payment import Payment
from models.wallet import Wallet
from models.campaign import Campaign
from decimal import Decimal


provider_service = ProviderService()
ledger_service = LedgerService()


@api_v1_bp.route("/checkout", methods=["GET"])
def hosted_checkout():
    """Hosted checkout page"""
    amount = request.args.get("amount", type=float)
    memo = request.args.get("memo", "")
    campaign_id = request.args.get("campaign_id", type=int)
    community_id = request.args.get("community_id", type=int)
    checkout_id = request.args.get("checkout_id") or str(uuid.uuid4())

    # Get available providers
    providers = provider_service.list_providers()

    # Get campaign details if provided
    campaign = None
    if campaign_id:
        campaign = Campaign.query.get(campaign_id)

    return render_template(
        "checkout.html",
        amount=amount,
        memo=memo,
        campaign=campaign,
        community_id=community_id,
        checkout_id=checkout_id,
        providers=providers,
    )


@api_v1_bp.route("/checkout/qr", methods=["GET"])
def generate_checkout_qr():
    """Generate QR code for checkout"""
    amount = request.args.get("amount", type=float)
    memo = request.args.get("memo", "")
    campaign_id = request.args.get("campaign_id", type=int)
    checkout_id = request.args.get("checkout_id") or str(uuid.uuid4())

    # Build checkout URL
    base_url = request.host_url.rstrip("/")
    checkout_url = f"{base_url}/checkout?amount={amount}&memo={memo}"
    if campaign_id:
        checkout_url += f"&campaign_id={campaign_id}"
    checkout_url += f"&checkout_id={checkout_id}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(checkout_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        "success": True,
        "qr_code": f"data:image/png;base64,{img_str}",
        "checkout_url": checkout_url,
        "checkout_id": checkout_id,
    })


@api_v1_bp.route("/checkout/initiate", methods=["POST"])
def initiate_checkout_payment():
    """Initiate payment from hosted checkout"""
    try:
        data = request.get_json() or {}
        amount = data.get("amount")
        phone = data.get("phone")
        provider = data.get("provider", "MPESA")
        memo = data.get("memo", "")
        campaign_id = data.get("campaign_id")
        checkout_id = data.get("checkout_id")

        if not amount or not phone or not provider:
            return (
                jsonify({"success": False, "message": "amount, phone, provider are required"}),
                400,
            )

        # Get or create temporary wallet for external payment
        # In production, this might create a temporary wallet or use community wallet
        wallet_id = None
        if campaign_id:
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                # Get community wallet
                from models.community import Community
                community = Community.query.get(campaign.community_id)
                if community:
                    wallet = Wallet.query.filter_by(
                        owner_type="COMMUNITY",
                        owner_id=community.id,
                    ).first()
                    if wallet:
                        wallet_id = wallet.id

        if not wallet_id:
            return jsonify({"success": False, "message": "Invalid campaign or wallet"}), 400

        # Create pending payment
        payment = Payment(
            payee_wallet_id=wallet_id,  # Receiving wallet
            amount=Decimal(str(amount)),
            currency="KES",
            status="PENDING",
            method="MOMO",
            provider=provider.upper(),
        )
        db.session.add(payment)
        db.session.flush()

        # Initiate provider payment
        adapter = provider_service.get_adapter(provider)
        if not adapter:
            return jsonify({"success": False, "message": "Provider not available"}), 400

        reference = f"CHECKOUT-{payment.id}-{checkout_id or uuid.uuid4()}"
        result = adapter.initiate_debit(
            phone=phone,
            amount=Decimal(str(amount)),
            currency="KES",
            reference=reference,
        )

        if result.success:
            payment.provider_ref = result.provider_ref
            db.session.commit()
            return jsonify({
                "success": True,
                "payment_id": payment.id,
                "status": "PENDING",
                "message": "Payment initiated. Check your phone for prompt.",
            }), 202
        else:
            payment.status = "FAILED"
            db.session.commit()
            return jsonify({"success": False, "message": result.message}), 400

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Payment initiation failed: {str(e)}"}),
            500,
        )

