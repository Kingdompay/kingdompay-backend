"""
Multi-signature approval routes
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from routes import api_v1_bp
from services.auth_service import AuthService
from services.multisig_service import MultiSigService
from extensions import db


auth_service = AuthService()
multisig_service = MultiSigService()


@api_v1_bp.route("/communities/<int:community_id>/approvals", methods=["POST"])
@jwt_required()
def create_approval_request(community_id: int):
    """Create multi-signature approval request"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        operation_type = data.get("operation_type")  # WITHDRAWAL|PAYOUT|DISBURSEMENT
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        destination = data.get("destination")
        description = data.get("description", "")
        operation_ref = data.get("operation_ref")
        required_signatures = data.get("required_signatures", 2)

        if not operation_type or not amount or not destination:
            return (
                jsonify({
                    "success": False,
                    "message": "operation_type, amount, destination are required",
                }),
                400,
            )

        result = multisig_service.create_approval_request(
            community_id=community_id,
            operation_type=operation_type,
            amount=amount,
            currency=currency,
            destination=destination,
            description=description,
            created_by=user.id,
            operation_ref=operation_ref,
            required_signatures=required_signatures,
        )

        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/approvals/<int:approval_id>/sign", methods=["POST"])
@jwt_required()
def sign_approval(approval_id: int):
    """Sign an approval request"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or {}
        signature_type = data.get("signature_type", "APPROVE")  # APPROVE|REJECT

        result = multisig_service.sign_approval(
            approval_id=approval_id,
            user_id=user.id,
            signature_type=signature_type,
        )

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/approvals/<int:approval_id>", methods=["GET"])
@jwt_required()
def get_approval_status(approval_id: int):
    """Get approval status and signatures"""
    try:
        result = multisig_service.get_approval_status(approval_id)

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/approvals/<int:approval_id>/execute", methods=["POST"])
@jwt_required()
def execute_approval(approval_id: int):
    """Execute an approved request"""
    try:
        user = auth_service.get_current_user()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        result = multisig_service.execute_approval(approval_id, executed_by=user.id)

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@api_v1_bp.route("/communities/<int:community_id>/approvals", methods=["GET"])
@jwt_required()
def list_community_approvals(community_id: int):
    """List approval requests for a community"""
    try:
        from models.multisig import MultiSigApproval
        status = request.args.get("status")
        operation_type = request.args.get("operation_type")

        query = MultiSigApproval.query.filter_by(community_id=community_id)

        if status:
            query = query.filter_by(status=status.upper())

        if operation_type:
            query = query.filter_by(operation_type=operation_type.upper())

        approvals = query.order_by(MultiSigApproval.created_at.desc()).limit(50).all()

        return jsonify({
            "success": True,
            "approvals": [a.to_dict() for a in approvals],
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

