"""
Fee and contribution routes
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from api.v1 import api_v1_bp
from services.auth_service import AuthService
from services.fee_service import FeeService
from services.rbac import require_admin, is_community_admin
from extensions import db
from decimal import Decimal


auth_service = AuthService()
fee_service = FeeService()


@api_v1_bp.route("/fees/calculate", methods=["POST"])
@jwt_required()
def calculate_fees():
    """Calculate transaction fees for a given amount"""
    try:
        data = request.get_json() or {}
        amount = data.get("amount")
        community_id = data.get("community_id")

        if not amount:
            return jsonify({"success": False, "message": "amount is required"}), 400

        fee_breakdown = fee_service.calculate_fees(
            Decimal(str(amount)),
            community_id=community_id,
        )

        return jsonify({"success": True, "fees": fee_breakdown}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/fees/validate-limits", methods=["POST"])
@jwt_required()
def validate_transaction_limits():
    """Validate transaction against limits"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        amount = data.get("amount")

        if not amount:
            return jsonify({"success": False, "message": "amount is required"}), 400

        result = fee_service.validate_transaction_limits(
            Decimal(str(amount)),
            user_id=user.id,
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/communities/<int:community_id>/cdf", methods=["GET"])
@jwt_required()
def get_community_development_fund(community_id: int):
    """Get Community Development Fund balance"""
    try:
        from models.fee import CommunityDevelopmentFund

        cdf = CommunityDevelopmentFund.query.filter_by(community_id=community_id).first()
        
        if not cdf:
            return jsonify({"success": False, "message": "CDF not found"}), 404

        return jsonify({"success": True, "cdf": cdf.to_dict()}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/communities/<int:community_id>/cdf/impact", methods=["GET"])
@jwt_required()
def get_cdf_impact(community_id: int):
    """Get CDF impact metrics"""
    try:
        from models.fee import CommunityContribution, CommunityDevelopmentFund
        from datetime import datetime, timedelta

        cdf = CommunityDevelopmentFund.query.filter_by(community_id=community_id).first()
        if not cdf:
            return jsonify({"success": False, "message": "CDF not found"}), 404

        # Get contributions in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_contributions = CommunityContribution.query.filter(
            CommunityContribution.community_id == community_id,
            CommunityContribution.created_at >= thirty_days_ago,
        ).all()

        # Calculate metrics
        total_contributions = sum(float(c.contribution_amount) for c in recent_contributions)
        education_count = len([c for c in recent_contributions if c.allocated_to == "EDUCATION"])
        health_count = len([c for c in recent_contributions if c.allocated_to == "HEALTH"])
        welfare_count = len([c for c in recent_contributions if c.allocated_to == "WELFARE"])

        # Estimate impact (example: KSh 5,000 per bursary, KSh 2,000 per health support)
        estimated_bursaries = int(float(cdf.education_balance) / 5000)
        estimated_health_supports = int(float(cdf.health_balance) / 2000)

        return jsonify({
            "success": True,
            "cdf": cdf.to_dict(),
            "metrics": {
                "total_contributed_30d": total_contributions,
                "recent_contributions_count": len(recent_contributions),
                "estimated_bursaries_funded": estimated_bursaries,
                "estimated_health_supports": estimated_health_supports,
                "education_allocation": float(cdf.education_balance),
                "health_allocation": float(cdf.health_balance),
                "welfare_allocation": float(cdf.welfare_balance),
            },
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/communities/<int:community_id>/cdf/contribution-rate", methods=["PUT"])
@jwt_required()
def update_contribution_rate(community_id: int):
    """Update community contribution rate (admin only)"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        if not is_community_admin(user.id, community_id):
            return jsonify({"success": False, "message": "Forbidden"}), 403

        data = request.get_json() or {}
        new_rate = data.get("contribution_rate")

        if new_rate is None or not (0 <= new_rate <= 0.1):  # Max 10%
            return jsonify({"success": False, "message": "Invalid rate (0-0.1)"}), 400

        from models.fee import CommunityDevelopmentFund

        cdf = CommunityDevelopmentFund.query.filter_by(community_id=community_id).first()
        if not cdf:
            cdf = CommunityDevelopmentFund(
                community_id=community_id,
                contribution_rate=Decimal(str(new_rate)),
            )
            db.session.add(cdf)
        else:
            cdf.contribution_rate = Decimal(str(new_rate))

        db.session.commit()

        return jsonify({"success": True, "cdf": cdf.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

