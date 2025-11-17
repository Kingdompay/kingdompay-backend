"""
Community routes for KingdomPay API v1
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from extensions import db
from models.community import Community, CommunityMember, CommunityRole
from models.community_invite import CommunityInvite
from services.rbac import is_community_admin


auth_service = AuthService()


@api_v1_bp.route("/communities", methods=["POST"])
@jwt_required()
def create_community():
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        name = data.get("name")
        ctype = data.get("type", "OTHER")
        slug = data.get("slug")
        settings = data.get("settings_json")

        if not name:
            return jsonify({"success": False, "message": "name is required"}), 400

        community = Community(
            name=name,
            type=ctype,
            slug=slug,
            owner_user_id=user.id,
            settings_json=settings,
        )
        db.session.add(community)
        db.session.flush()

        member = CommunityMember(
            community_id=community.id, user_id=user.id, role=CommunityRole.ADMIN.value
        )
        db.session.add(member)
        db.session.flush()

        # Create community wallet
        from services.wallet_service import WalletService

        community_wallet = WalletService.get_or_create_community_wallet(community.id)

        db.session.commit()

        community_dict = community.to_dict()
        if community_wallet:
            community_dict["wallet_id"] = community_wallet.id
            community_dict["wallet_display_number"] = community_wallet.display_number

        return jsonify({"success": True, "community": community_dict}), 201
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


@api_v1_bp.route("/communities", methods=["GET"])
@jwt_required()
def list_communities():
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        q = (
            db.session.query(Community)
            .join(CommunityMember, CommunityMember.community_id == Community.id)
            .filter(CommunityMember.user_id == user.id)
            .all()
        )
        return jsonify({"success": True, "communities": [c.to_dict() for c in q]}), 200
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


@api_v1_bp.route("/communities/<int:community_id>", methods=["GET"])
@jwt_required()
def get_community(community_id: int):
    try:
        community = Community.query.get(community_id)
        if not community:
            return jsonify({"success": False, "message": "Community not found"}), 404
        return jsonify({"success": True, "community": community.to_dict()}), 200
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


@api_v1_bp.route("/communities/<int:community_id>", methods=["PUT"])
@jwt_required()
def update_community(community_id: int):
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        community = Community.query.get(community_id)
        if not community:
            return jsonify({"success": False, "message": "Community not found"}), 404

        # Enforce RBAC (Admin/Treasurer only)
        if not is_community_admin(user.id, community.id):
            return jsonify({"success": False, "message": "Forbidden"}), 403
        data = request.get_json() or {}
        if "name" in data:
            community.name = data["name"]
        if "type" in data:
            community.type = data["type"]
        if "settings_json" in data:
            community.settings_json = data["settings_json"]
        db.session.commit()
        return jsonify({"success": True, "community": community.to_dict()}), 200
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


@api_v1_bp.route("/communities/<int:community_id>", methods=["DELETE"])
@jwt_required()
def delete_community(community_id: int):
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        community = Community.query.get(community_id)
        if not community:
            return jsonify({"success": False, "message": "Community not found"}), 404

        # Enforce RBAC (Admin only)
        if not (
            CommunityMember.query.filter_by(
                community_id=community.id,
                user_id=user.id,
                role=CommunityRole.ADMIN.value,
            ).first()
        ):
            return jsonify({"success": False, "message": "Forbidden"}), 403
        db.session.delete(community)
        db.session.commit()
        return jsonify({"success": True}), 200
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


@api_v1_bp.route("/communities/<int:community_id>/invite", methods=["POST"])
@jwt_required()
def create_invite(community_id: int):
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        community = Community.query.get(community_id)
        if not community:
            return jsonify({"success": False, "message": "Community not found"}), 404

        # Enforce RBAC (Admin/Treasurer only)
        if not is_community_admin(user.id, community.id):
            return jsonify({"success": False, "message": "Forbidden"}), 403
        ttl = int((request.get_json() or {}).get("ttl_minutes", 1440))
        invite = CommunityInvite.create_invite(community_id, user.id, ttl)
        # Placeholder join URL (to be used by mobile/web to open join flow)
        join_url = f"/join/{invite.token}"
        return (
            jsonify(
                {
                    "success": True,
                    "invite": {
                        "token": invite.token,
                        "join_url": join_url,
                        "expires_at": invite.expires_at.isoformat(),
                    },
                }
            ),
            201,
        )
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


@api_v1_bp.route("/communities/join", methods=["POST"])
@jwt_required()
def join_by_token():
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        token = (request.get_json() or {}).get("token")
        if not token:
            return jsonify({"success": False, "message": "token is required"}), 400

        invite = CommunityInvite.validate_token(token)
        if not invite:
            return (
                jsonify({"success": False, "message": "Invalid or expired invite"}),
                400,
            )

        # Upsert membership
        existing = CommunityMember.query.filter_by(
            community_id=invite.community_id, user_id=user.id
        ).first()
        if not existing:
            member = CommunityMember(
                community_id=invite.community_id,
                user_id=user.id,
                role=CommunityRole.MEMBER.value,
            )
            db.session.add(member)
        # Mark invite as used
        invite.status = "USED"
        db.session.commit()
        return jsonify({"success": True, "community_id": invite.community_id}), 200
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


@api_v1_bp.route("/communities/<int:community_id>/contributions", methods=["GET"])
@jwt_required()
def list_contributions(community_id: int):
    """List contributions for a community"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Check if user is a member
        membership = CommunityMember.query.filter_by(
            community_id=community_id, user_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "message": "Not a community member"}), 403

        from models.community import Contribution
        contributions = Contribution.query.filter_by(
            community_id=community_id
        ).order_by(Contribution.created_at.desc()).limit(100).all()

        return jsonify({
            "success": True,
            "contributions": [c.to_dict() for c in contributions]
        }), 200
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while processing your request",
                }
            ),
            500,
        )


@api_v1_bp.route("/communities/<int:community_id>/contributions", methods=["POST"])
@jwt_required()
def create_contribution(community_id: int):
    """Create a contribution to a community"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Check if user is a member
        membership = CommunityMember.query.filter_by(
            community_id=community_id, user_id=user.id
        ).first()
        if not membership:
            return jsonify({"success": False, "message": "Not a community member"}), 403

        data = request.get_json() or {}
        amount = data.get("amount")
        description = data.get("description", "")

        if not amount:
            return jsonify({"success": False, "message": "amount is required"}), 400

        # Get user wallet
        from models.wallet import Wallet
        from_wallet = Wallet.find_by_user_id(user.id)
        if not from_wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Get or create community wallet
        from services.wallet_service import WalletService
        community_wallet = WalletService.get_or_create_community_wallet(community_id)
        if not community_wallet:
            return jsonify({"success": False, "message": "Community wallet not found"}), 404

        # Use TransferService for the contribution
        from services.transfer_service import TransferService
        from decimal import Decimal
        import uuid

        transfer_service = TransferService()
        idempotency_key = str(uuid.uuid4())

        result = transfer_service.process_transfer(
            from_wallet_id=from_wallet.id,
            to_wallet_id=community_wallet.id,
            amount=Decimal(str(amount)),
            currency=from_wallet.currency,
            memo=description or f"Contribution to community",
            idempotency_key=idempotency_key,
            user_id=user.id,
            external_ref=f"COMMUNITY-{community_id}",
        )

        if result.get("success"):
            # Create contribution record
            from models.community import Contribution
            contribution = Contribution(
                community_id=community_id,
                user_id=user.id,
                amount=Decimal(str(amount)),
                description=description,
                journal_id=result.get("journal_id"),
            )
            db.session.add(contribution)
            db.session.commit()

            return jsonify({
                "success": True,
                "contribution": contribution.to_dict(),
                "journal_id": result.get("journal_id")
            }), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }
            ),
            500,
        )
