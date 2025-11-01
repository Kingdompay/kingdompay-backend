"""
Campaign routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from api.v1 import api_v1_bp
from services.auth_service import AuthService
from extensions import db
from models.campaign import Campaign
from models.wallet import Wallet
from services.ledger_service import LedgerService
from services.receipt_service import ReceiptService
from services.notifications_service import NotificationsService
from models.community import Community, CommunityMember


auth_service = AuthService()
ledger_service = LedgerService()
receipt_service = ReceiptService()
notifications = NotificationsService()


@api_v1_bp.route("/campaigns", methods=["POST"])
@jwt_required()
def create_campaign():
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        community_id = data.get("community_id")
        title = data.get("title")
        ctype = data.get("type")
        target = data.get("target_amount")

        if not community_id or not title or not ctype:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "community_id, title, type are required",
                    }
                ),
                400,
            )

        # Ensure user is a member of the community
        membership = CommunityMember.query.filter_by(
            community_id=community_id, user_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "message": "Not a community member"}), 403

        campaign = Campaign(
            community_id=community_id, title=title, type=ctype, target_amount=target
        )
        db.session.add(campaign)
        db.session.commit()
        return jsonify({"success": True, "campaign": campaign.to_dict()}), 201
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


@api_v1_bp.route("/communities/<int:community_id>/campaigns", methods=["GET"])
@jwt_required()
def list_campaigns(community_id: int):
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Must be a member
        membership = CommunityMember.query.filter_by(
            community_id=community_id, user_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "message": "Not a community member"}), 403

        cs = (
            Campaign.query.filter_by(community_id=community_id)
            .order_by(Campaign.created_at.desc())
            .all()
        )
        return jsonify({"success": True, "campaigns": [c.to_dict() for c in cs]}), 200
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/campaigns/<int:campaign_id>", methods=["GET"])
@jwt_required()
def get_campaign(campaign_id: int):
    try:
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return jsonify({"success": False, "message": "Campaign not found"}), 404
        return jsonify({"success": True, "campaign": campaign.to_dict()}), 200
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/campaigns/<int:campaign_id>/contribute", methods=["POST"])
@jwt_required()
def contribute_to_campaign(campaign_id: int):
    """Contribute from current user's wallet to the community wallet via journal posting"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return jsonify({"success": False, "message": "Campaign not found"}), 404

        # Ensure membership
        membership = CommunityMember.query.filter_by(
            community_id=campaign.community_id, user_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "message": "Not a community member"}), 403

        data = request.get_json() or {}
        amount = data.get("amount")
        currency = data.get("currency")
        memo = data.get("memo") or f"Contribution to campaign {campaign.title}"
        idem_key = request.headers.get("Idempotency-Key")
        if not amount:
            return jsonify({"success": False, "message": "amount is required"}), 400
        if not idem_key:
            return (
                jsonify(
                    {"success": False, "message": "Idempotency-Key header required"}
                ),
                400,
            )

        # Resolve wallets: contributor (user) and community wallet (owner user or dedicated wallet)
        from_wallet = Wallet.find_by_user_id(user.id)
        if not from_wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # For MVP, use the community owner's wallet as community wallet
        community = Community.query.get(campaign.community_id)
        to_wallet = Wallet.find_by_user_id(community.owner_user_id)
        if not to_wallet:
            return (
                jsonify({"success": False, "message": "Community wallet not found"}),
                404,
            )

        result = ledger_service.post_transfer(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=amount,
            currency=currency or from_wallet.currency,
            memo=memo,
            idempotency_key=idem_key,
            meta={"campaign_id": campaign.id},
        )
        status_code = 200 if result.get("success") else 400
        # Send basic receipts if available
        if result.get("success") and result.get("journal_id"):
            try:
                receipt = receipt_service.build_receipt(
                    journal_id=result["journal_id"], campaign=campaign
                )
                if user.email:
                    receipt_service.send_email_receipt(
                        to_email=user.email,
                        subject="Contribution Receipt",
                        body=f"Thank you for your contribution. Journal #{receipt['journal_id']}",
                    )
                if user.phone_number:
                    receipt_service.send_sms_receipt(
                        phone=user.phone_number,
                        body=f"Thanks! Contribution recorded. J#{receipt['journal_id']}",
                    )
                notifications.notify_contribution_success(
                    phone=user.phone_number, amount=str(amount)
                )
            except Exception:
                pass
        return jsonify(result), status_code
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )
