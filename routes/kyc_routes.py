"""
KYC API Routes for KingdomPay
Handles Know Your Customer verification endpoints
"""

from datetime import datetime
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os

from routes import api_v1_bp
from extensions import db
from services.kyc_service import KYCService
from models.kyc import DocumentType, KYCStatus, KYCTier

kyc_service = KYCService()


@api_v1_bp.route("/kyc/status", methods=["GET"])
@jwt_required()
def get_kyc_status():
    """
    Get user's KYC verification status
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    responses:
      200:
        description: KYC status and documents
        schema:
          type: object
          properties:
            verification:
              type: object
              properties:
                status:
                  type: string
                  enum: [pending, approved, rejected]
                tier:
                  type: string
                  enum: [tier_0, tier_1, tier_2]
                daily_limit:
                  type: number
            documents:
              type: array
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        result = kyc_service.get_user_kyc_status(user_id)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get KYC status: {e}")
        return jsonify({"error": "Failed to get KYC status"}), 500


@api_v1_bp.route("/kyc/initiate", methods=["POST"])
@jwt_required()
def initiate_kyc():
    """
    Initiate KYC verification process
    ---
    tags:
      - KYC
    security:
      - Bearer: []
    responses:
      201:
        description: KYC verification initiated
      400:
        description: Already initiated
      401:
        description: Unauthorized
    """
    try:
        user_id = get_jwt_identity()
        result = kyc_service.create_kyc_verification(user_id)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201
    except Exception as e:
        current_app.logger.error(f"Failed to initiate KYC: {e}")
        return jsonify({"error": "Failed to initiate KYC"}), 500


@api_v1_bp.route("/kyc/documents", methods=["POST"])
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


@api_v1_bp.route("/kyc/documents/<int:document_id>", methods=["GET"])
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


@api_v1_bp.route("/kyc/verify", methods=["POST"])
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


@api_v1_bp.route("/kyc/upgrade", methods=["POST"])
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


@api_v1_bp.route("/kyc/limits/check", methods=["GET", "POST"])
@jwt_required()
def check_transaction_limits():
    """Check if transaction is within KYC limits"""
    try:
        user_id = get_jwt_identity()

        # Support both GET query params and POST JSON body
        if request.method == "GET":
            amount = request.args.get("amount")
            transaction_type = request.args.get("transaction_type", "transfer")
        else:
            data = request.get_json() or {}
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


@api_v1_bp.route("/kyc/audit-trail", methods=["GET"])
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


@api_v1_bp.route("/kyc/documents/types", methods=["GET"])
@api_v1_bp.route("/kyc/document-types", methods=["GET"])  # Alias route
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


@api_v1_bp.route("/kyc/tiers", methods=["GET"])
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


# ═══════════════════════════════════════════════════════════════════════════
#                         ADMIN KYC MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

from services.rbac import require_admin
from models.kyc import KYCDocument, KYCVerification


@api_v1_bp.route("/admin/kyc/pending-documents", methods=["GET"])
@jwt_required()
@require_admin
def get_pending_documents():
    """Get all pending KYC documents for admin review"""
    try:
        # Get all documents (both pending and processed) for admin view
        # Default to pending only, but allow ?all=true to get all
        show_all = request.args.get('all', 'false').lower() == 'true'
        
        if show_all:
            docs = KYCDocument.query.order_by(KYCDocument.uploaded_at.desc()).all()
        else:
            docs = KYCDocument.query.filter_by(status="pending").order_by(
                KYCDocument.uploaded_at.desc()
            ).all()
        
        # Enrich with user info
        documents = []
        for doc in docs:
            doc_dict = doc.to_dict()
            # Add user info at top level for easier frontend access
            from models.user import User
            user = User.query.get(doc.user_id)
            if user:
                doc_dict["user_name"] = user.full_name
                doc_dict["user_phone"] = user.phone_number
                doc_dict["user_email"] = user.email
                doc_dict["user"] = {
                    "id": user.id,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "email": user.email
                }
            else:
                doc_dict["user_name"] = "Unknown User"
            documents.append(doc_dict)
        
        return jsonify({
            "success": True,
            "count": len(documents),
            "documents": documents
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get pending documents: {e}")
        return jsonify({"error": "Failed to get pending documents"}), 500


@api_v1_bp.route("/admin/kyc/pending-verifications", methods=["GET"])
@jwt_required()
@require_admin
def get_pending_verifications():
    """Get all pending KYC verifications for admin review"""
    try:
        pending = KYCVerification.query.filter_by(status="pending").order_by(
            KYCVerification.created_at.desc()
        ).all()
        
        verifications = []
        for v in pending:
            v_dict = v.to_dict()
            # Add user info
            from models.user import User
            user = User.query.get(v.user_id)
            if user:
                v_dict["user"] = {
                    "id": user.id,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "email": user.email
                }
            # Add document count
            docs = KYCDocument.query.filter_by(user_id=v.user_id).all()
            v_dict["documents"] = [d.to_dict() for d in docs]
            verifications.append(v_dict)
        
        return jsonify({
            "success": True,
            "pending_count": len(verifications),
            "verifications": verifications
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get pending verifications: {e}")
        return jsonify({"error": "Failed to get pending verifications"}), 500


@api_v1_bp.route("/admin/kyc/stats", methods=["GET"])
@jwt_required()
@require_admin
def get_kyc_stats():
    """Get KYC statistics for admin dashboard"""
    try:
        from sqlalchemy import func
        
        # Document stats
        pending_docs = KYCDocument.query.filter_by(status="pending").count()
        approved_docs = KYCDocument.query.filter_by(status="approved").count()
        rejected_docs = KYCDocument.query.filter_by(status="rejected").count()
        
        # Verification stats
        pending_verifications = KYCVerification.query.filter_by(status="pending").count()
        approved_verifications = KYCVerification.query.filter_by(status="approved").count()
        
        # Tier distribution
        tier_0 = KYCVerification.query.filter_by(tier="tier_0").count()
        tier_1 = KYCVerification.query.filter_by(tier="tier_1").count()
        tier_2 = KYCVerification.query.filter_by(tier="tier_2").count()
        
        return jsonify({
            "success": True,
            "stats": {
                "documents": {
                    "pending": pending_docs,
                    "approved": approved_docs,
                    "rejected": rejected_docs,
                    "total": pending_docs + approved_docs + rejected_docs
                },
                "verifications": {
                    "pending": pending_verifications,
                    "approved": approved_verifications,
                    "total": pending_verifications + approved_verifications
                },
                "tier_distribution": {
                    "tier_0": tier_0,
                    "tier_1": tier_1,
                    "tier_2": tier_2
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get KYC stats: {e}")
        return jsonify({"error": "Failed to get KYC stats"}), 500


@api_v1_bp.route("/admin/kyc/document/<int:document_id>/view", methods=["GET"])
@jwt_required()
@require_admin
def view_document_file(document_id):
    """View/download a KYC document file (admin only)"""
    try:
        document = KYCDocument.query.get(document_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            return jsonify({"error": "Document file not found on server"}), 404
        
        from flask import send_file
        return send_file(
            document.file_path,
            mimetype=document.mime_type,
            as_attachment=False
        )
        
    except Exception as e:
        current_app.logger.error(f"Failed to view document: {e}")
        return jsonify({"error": "Failed to view document"}), 500


@api_v1_bp.route("/admin/kyc/document/<int:document_id>/verify", methods=["POST"])
@jwt_required()
@require_admin
def admin_verify_document(document_id):
    """Approve or reject a KYC document (admin only)"""
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or "status" not in data:
            return jsonify({"error": "Status is required (approved/rejected)"}), 400
        
        status = data["status"].lower()
        if status not in ["approved", "rejected"]:
            return jsonify({"error": "Status must be 'approved' or 'rejected'"}), 400
        
        rejection_reason = data.get("rejection_reason")
        
        # Get the document to find user_id
        document = KYCDocument.query.get(document_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        user_id = document.user_id
        
        # Verify the document using the KYC service
        result = kyc_service.verify_document(
            document_id=document_id,
            verifier_id=admin_id,
            status=status,
            rejection_reason=rejection_reason
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        # If document was approved, check if we should update KYC verification status
        if status == "approved":
            # Check if user has at least one approved document (basic ID requirement)
            approved_docs = KYCDocument.query.filter_by(
                user_id=user_id, 
                status="approved"
            ).count()
            
            if approved_docs >= 1:
                # Update KYC verification status to approved
                kyc_verification = KYCVerification.query.filter_by(user_id=user_id).first()
                if kyc_verification:
                    kyc_verification.status = KYCStatus.APPROVED.value
                    kyc_verification.tier = KYCTier.TIER_1.value  # Upgrade to Tier 1
                    kyc_verification.verified_by = int(admin_id)
                    kyc_verification.verified_at = datetime.utcnow()
                    # Set transaction limits for Tier 1
                    kyc_verification.daily_limit = current_app.config.get("KYC_TIER_1_LIMIT", 100000)
                    kyc_verification.monthly_limit = current_app.config.get("KYC_TIER_1_LIMIT", 100000)
                    kyc_verification.yearly_limit = current_app.config.get("KYC_TIER_1_LIMIT", 100000)
                    db.session.commit()
                    
                    current_app.logger.info(f"User {user_id} KYC verification approved and upgraded to Tier 1")
        
        return jsonify({
            "success": True,
            "message": f"Document {status} successfully",
            "document": result
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to verify document: {e}")
        return jsonify({"error": "Failed to verify document"}), 500


# ═══════════════════════════════════════════════════════════════════════════
#                         ADMIN USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

from models.user import User

@api_v1_bp.route("/admin/users", methods=["GET"])
@jwt_required()
@require_admin
def get_all_users():
    """Get all users for admin dashboard"""
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        
        # Base query
        query = User.query
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.full_name.ilike(search_term),
                    User.phone_number.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Apply role filter
        if role_filter:
            query = query.filter(User.role == role_filter.upper())
        
        # Order by most recent first
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Build user list with KYC status
        users = []
        for user in pagination.items:
            user_dict = user.to_dict()
            
            # Add KYC status
            kyc = KYCVerification.query.filter_by(user_id=user.id).first()
            if kyc:
                user_dict["kyc_status"] = kyc.status
                user_dict["kyc_tier"] = kyc.tier
            else:
                user_dict["kyc_status"] = "not_initiated"
                user_dict["kyc_tier"] = None
            
            # Add document count
            doc_count = KYCDocument.query.filter_by(user_id=user.id).count()
            user_dict["document_count"] = doc_count
            
            # Add wallet info
            if user.wallet:
                user_dict["wallet_balance"] = float(user.wallet.balance or 0)
                user_dict["wallet_number"] = user.wallet.wallet_number
            else:
                user_dict["wallet_balance"] = 0
                user_dict["wallet_number"] = None
            
            users.append(user_dict)
        
        return jsonify({
            "success": True,
            "users": users,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get users: {e}")
        return jsonify({"error": "Failed to get users"}), 500


@api_v1_bp.route("/admin/users/<int:user_id>", methods=["GET"])
@jwt_required()
@require_admin
def get_user_details(user_id):
    """Get detailed information about a specific user"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_dict = user.to_dict()
        
        # Add KYC info
        kyc = KYCVerification.query.filter_by(user_id=user.id).first()
        if kyc:
            user_dict["kyc"] = kyc.to_dict()
        else:
            user_dict["kyc"] = None
        
        # Add documents
        documents = KYCDocument.query.filter_by(user_id=user.id).all()
        user_dict["documents"] = [doc.to_dict() for doc in documents]
        
        # Add wallet info
        if user.wallet:
            user_dict["wallet"] = {
                "id": user.wallet.id,
                "wallet_number": user.wallet.wallet_number,
                "balance": float(user.wallet.balance or 0),
                "currency": user.wallet.currency,
                "created_at": user.wallet.created_at.isoformat() if user.wallet.created_at else None
            }
        else:
            user_dict["wallet"] = None
        
        # Add community memberships
        memberships = []
        for membership in user.community_memberships:
            if membership.community:
                memberships.append({
                    "community_id": membership.community_id,
                    "community_name": membership.community.name,
                    "role": membership.role,
                    "joined_at": membership.joined_at.isoformat() if membership.joined_at else None
                })
        user_dict["communities"] = memberships
        
        return jsonify({
            "success": True,
            "user": user_dict
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get user details: {e}")
        return jsonify({"error": "Failed to get user details"}), 500


@api_v1_bp.route("/admin/users/stats", methods=["GET"])
@jwt_required()
@require_admin
def get_user_stats():
    """Get user statistics for admin dashboard"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        verified_users = User.query.filter_by(is_phone_verified=True).count()
        admin_users = User.query.filter_by(role="ADMIN").count()
        
        # KYC stats
        kyc_approved = KYCVerification.query.filter_by(status="approved").count()
        kyc_pending = KYCVerification.query.filter_by(status="pending").count()
        
        # Recent registrations (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= seven_days_ago).count()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_users": total_users,
                "active_users": active_users,
                "verified_users": verified_users,
                "admin_users": admin_users,
                "kyc_approved": kyc_approved,
                "kyc_pending": kyc_pending,
                "recent_registrations": recent_users
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get user stats: {e}")
        return jsonify({"error": "Failed to get user stats"}), 500
