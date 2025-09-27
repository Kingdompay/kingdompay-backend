"""
KYC API Routes for KingdomPay
Handles Know Your Customer verification endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os

from services.kyc_service import KYCService
from models.kyc import DocumentType, KYCStatus, KYCTier

kyc_bp = Blueprint("kyc", __name__)
kyc_service = KYCService()


@kyc_bp.route("/kyc/status", methods=["GET"])
@jwt_required()
def get_kyc_status():
    """Get user's KYC status and documents"""
    try:
        user_id = get_jwt_identity()
        result = kyc_service.get_user_kyc_status(user_id)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get KYC status: {e}")
        return jsonify({"error": "Failed to get KYC status"}), 500


@kyc_bp.route("/kyc/initiate", methods=["POST"])
@jwt_required()
def initiate_kyc():
    """Initiate KYC verification process"""
    try:
        user_id = get_jwt_identity()
        result = kyc_service.create_kyc_verification(user_id)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201
    except Exception as e:
        current_app.logger.error(f"Failed to initiate KYC: {e}")
        return jsonify({"error": "Failed to initiate KYC"}), 500


@kyc_bp.route("/kyc/documents", methods=["POST"])
@jwt_required()
def upload_document():
    """Upload KYC document"""
    try:
        user_id = get_jwt_identity()

        # Validate request
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        document_type = request.form.get("document_type")

        if not document_type:
            return jsonify({"error": "Document type required"}), 400

        # Validate document type
        try:
            DocumentType(document_type)
        except ValueError:
            return jsonify({"error": "Invalid document type"}), 400

        # Upload document
        result = kyc_service.upload_document(
            user_id=user_id,
            file=file,
            document_type=document_type,
            metadata=request.form.get("metadata"),
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201
    except Exception as e:
        current_app.logger.error(f"Failed to upload document: {e}")
        return jsonify({"error": "Failed to upload document"}), 500


@kyc_bp.route("/kyc/documents/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    """Get document information"""
    try:
        user_id = get_jwt_identity()

        # Import here to avoid circular imports
        from models.kyc import KYCDocument

        document = KYCDocument.query.filter_by(id=document_id, user_id=user_id).first()

        if not document:
            return jsonify({"error": "Document not found"}), 404

        return jsonify(document.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get document: {e}")
        return jsonify({"error": "Failed to get document"}), 500


@kyc_bp.route("/kyc/verify", methods=["POST"])
@jwt_required()
def verify_document():
    """Verify a KYC document (admin only)"""
    try:
        verifier_id = get_jwt_identity()

        data = request.get_json()
        document_id = data.get("document_id")
        status = data.get("status")
        rejection_reason = data.get("rejection_reason")
        extracted_data = data.get("extracted_data")

        if not all([document_id, status]):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate status
        try:
            KYCStatus(status)
        except ValueError:
            return jsonify({"error": "Invalid status"}), 400

        result = kyc_service.verify_document(
            document_id=document_id,
            verifier_id=verifier_id,
            status=status,
            rejection_reason=rejection_reason,
            extracted_data=extracted_data,
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to verify document: {e}")
        return jsonify({"error": "Failed to verify document"}), 500


@kyc_bp.route("/kyc/upgrade", methods=["POST"])
@jwt_required()
def upgrade_kyc_tier():
    """Upgrade user's KYC tier (admin only)"""
    try:
        verifier_id = get_jwt_identity()

        data = request.get_json()
        user_id = data.get("user_id")
        new_tier = data.get("tier")
        personal_data = data.get("personal_data")

        if not all([user_id, new_tier]):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate tier
        try:
            KYCTier(new_tier)
        except ValueError:
            return jsonify({"error": "Invalid tier"}), 400

        result = kyc_service.upgrade_kyc_tier(
            user_id=user_id,
            new_tier=new_tier,
            verifier_id=verifier_id,
            personal_data=personal_data,
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to upgrade KYC tier: {e}")
        return jsonify({"error": "Failed to upgrade KYC tier"}), 500


@kyc_bp.route("/kyc/limits/check", methods=["POST"])
@jwt_required()
def check_transaction_limits():
    """Check if transaction is within KYC limits"""
    try:
        user_id = get_jwt_identity()

        data = request.get_json()
        amount = data.get("amount")
        transaction_type = data.get("transaction_type", "transfer")

        if not amount:
            return jsonify({"error": "Amount required"}), 400

        try:
            amount = float(amount)
        except ValueError:
            return jsonify({"error": "Invalid amount"}), 400

        result = kyc_service.check_transaction_limits(
            user_id=user_id, amount=amount, transaction_type=transaction_type
        )

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to check transaction limits: {e}")
        return jsonify({"error": "Failed to check transaction limits"}), 500


@kyc_bp.route("/kyc/audit-trail", methods=["GET"])
@jwt_required()
def get_audit_trail():
    """Get KYC audit trail for user"""
    try:
        user_id = get_jwt_identity()
        limit = request.args.get("limit", 50, type=int)

        audit_logs = kyc_service.get_kyc_audit_trail(user_id, limit)

        return jsonify({"audit_logs": audit_logs}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get audit trail: {e}")
        return jsonify({"error": "Failed to get audit trail"}), 500


@kyc_bp.route("/kyc/documents/types", methods=["GET"])
def get_document_types():
    """Get supported document types"""
    try:
        document_types = [
            {
                "value": doc_type.value,
                "label": doc_type.value.replace("_", " ").title(),
                "description": _get_document_description(doc_type),
            }
            for doc_type in DocumentType
        ]

        return jsonify({"document_types": document_types}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get document types: {e}")
        return jsonify({"error": "Failed to get document types"}), 500


@kyc_bp.route("/kyc/tiers", methods=["GET"])
def get_kyc_tiers():
    """Get KYC tier information"""
    try:
        tiers = [
            {
                "value": tier.value,
                "label": tier.value.replace("_", " ").title(),
                "limits": _get_tier_limits(tier),
            }
            for tier in KYCTier
        ]

        return jsonify({"tiers": tiers}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get KYC tiers: {e}")
        return jsonify({"error": "Failed to get KYC tiers"}), 500


def _get_document_description(doc_type: DocumentType) -> str:
    """Get description for document type"""
    descriptions = {
        DocumentType.NATIONAL_ID: "Government-issued national identification document",
        DocumentType.PASSPORT: "Valid passport from any country",
        DocumentType.DRIVERS_LICENSE: "Valid driver's license",
        DocumentType.UTILITY_BILL: "Recent utility bill (electricity, water, gas)",
        DocumentType.BANK_STATEMENT: "Recent bank statement showing account activity",
        DocumentType.EMPLOYMENT_LETTER: "Employment verification letter from employer",
    }
    return descriptions.get(doc_type, "Document verification")


def _get_tier_limits(tier: KYCTier) -> dict:
    """Get limits for KYC tier"""
    config = current_app.config

    if tier == KYCTier.TIER_0:
        limit = config.get("KYC_TIER_0_LIMIT", 10000)
    elif tier == KYCTier.TIER_1:
        limit = config.get("KYC_TIER_1_LIMIT", 100000)
    elif tier == KYCTier.TIER_2:
        limit = config.get("KYC_TIER_2_LIMIT", 1000000)
    else:
        limit = 0

    return {
        "daily_limit": float(limit),
        "monthly_limit": float(limit),
        "yearly_limit": float(limit),
        "currency": config.get("DEFAULT_CURRENCY", "KES"),
    }
