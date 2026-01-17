"""
KYC Service for KingdomPay
Handles Know Your Customer verification and compliance
"""

import os
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import and_, or_
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

from models.kyc import (
    KYCVerification,
    KYCDocument,
    KYCAuditLog,
    KYCStatus,
    KYCTier,
    DocumentType,
)
from services.encryption_service import EncryptionService
from extensions import db

logger = logging.getLogger(__name__)


class KYCService:
    """Service for KYC verification and compliance management"""

    def __init__(self):
        self.encryption_service = EncryptionService()
        self.allowed_extensions = {"png", "jpg", "jpeg", "pdf", "tiff", "bmp"}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self._setup_upload_folder()

    def _setup_upload_folder(self):
        """Setup upload folder with app context"""
        try:
            self.upload_folder = os.path.join(
                current_app.config.get("BASE_DIR", ""), "uploads", "kyc"
            )
        except RuntimeError:
            # Fallback when outside app context
            self.upload_folder = os.path.join(os.getcwd(), "uploads", "kyc")

        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)

    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in self.allowed_extensions
        )

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _get_risk_score(self, user_data: Dict[str, Any]) -> Tuple[float, str]:
        """Calculate risk score based on user data"""
        score = 0.0

        # Age factor
        if user_data.get("age", 0) < 18:
            score += 30
        elif user_data.get("age", 0) > 65:
            score += 10

        # Country risk (simplified)
        high_risk_countries = ["AF", "IR", "KP", "SY"]  # Example high-risk countries
        if user_data.get("country_code") in high_risk_countries:
            score += 40

        # PEP status
        if user_data.get("is_pep", False):
            score += 25

        # Sanctions check
        if user_data.get("sanctions_match", False):
            score += 50

        # Determine risk level
        if score >= 70:
            risk_level = "high"
        elif score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return min(score, 100.0), risk_level

    def create_kyc_verification(self, user_id: int) -> Dict[str, Any]:
        """Create initial KYC verification record"""
        try:
            # Check if verification already exists
            existing = KYCVerification.query.filter_by(user_id=user_id).first()
            if existing:
                return {"error": "KYC verification already exists for this user"}

            # Create new verification record
            kyc_verification = KYCVerification(
                user_id=user_id,
                tier=KYCTier.TIER_0.value,
                status=KYCStatus.PENDING.value,
                daily_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
                monthly_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
                yearly_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
            )

            db.session.add(kyc_verification)
            db.session.commit()

            # Log the action
            self._log_kyc_action(
                user_id=user_id,
                action="kyc_verification_created",
                kyc_verification_id=kyc_verification.id,
                metadata={"tier": KYCTier.TIER_0.value},
            )

            return kyc_verification.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create KYC verification: {e}")
            return {"error": "Failed to create KYC verification"}

    def upload_document(
        self,
        user_id: int,
        file,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload and process KYC document"""
        try:
            # Convert user_id to int if it's a string
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return {"error": "Invalid user ID"}
            
            # Validate file
            if not file or not file.filename:
                return {"error": "No file provided"}

            if not self._allowed_file(file.filename):
                return {"error": "File type not allowed"}

            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning

            if file_size > self.max_file_size:
                return {"error": "File too large"}

            # Validate document type
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                return {"error": "Invalid document type"}

            # Generate secure filename
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{user_id}_{doc_type.value}_{timestamp}_{filename}"
            file_path = os.path.join(self.upload_folder, unique_filename)

            # Save file
            file.save(file_path)

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            # Check for duplicate files (but allow re-upload of rejected documents)
            existing_doc = KYCDocument.query.filter_by(
                user_id=user_id, 
                document_type=doc_type.value
            ).first()
            
            if existing_doc:
                if existing_doc.status == "rejected":
                    # Allow re-upload - delete old record
                    db.session.delete(existing_doc)
                    db.session.commit()
                    logger.info(f"Deleted rejected document {existing_doc.id} for re-upload")
                elif existing_doc.status == "pending":
                    os.remove(file_path)
                    return {"error": "You already have a pending document of this type"}
                elif existing_doc.status == "approved":
                    os.remove(file_path)
                    return {"error": "You already have an approved document of this type"}

            # Check for exact duplicate by hash
            hash_duplicate = KYCDocument.query.filter_by(file_hash=file_hash).first()
            if hash_duplicate and hash_duplicate.user_id != user_id:
                os.remove(file_path)
                return {"error": "This document has already been used by another user"}

            # Auto-create KYC verification record if it doesn't exist
            kyc_verification = KYCVerification.query.filter_by(user_id=user_id).first()
            if not kyc_verification:
                kyc_verification = KYCVerification(
                    user_id=user_id,
                    tier=KYCTier.TIER_0.value,
                    status=KYCStatus.PENDING.value,
                    daily_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
                    monthly_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
                    yearly_limit=current_app.config.get("KYC_TIER_0_LIMIT", 10000),
                )
                db.session.add(kyc_verification)
                db.session.flush()  # Get ID without committing
                logger.info(f"Auto-created KYC verification record for user {user_id}")
            else:
                # If KYC was rejected, reset it to pending when new document is uploaded
                if kyc_verification.status == "rejected":
                    kyc_verification.status = KYCStatus.PENDING.value
                    logger.info(f"Reset KYC verification status to pending for user {user_id}")

            # Create document record
            kyc_document = KYCDocument(
                user_id=user_id,
                document_type=doc_type.value,
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                extracted_data=metadata,
                status=KYCStatus.PENDING.value,
            )

            db.session.add(kyc_document)
            db.session.commit()

            # Log the action
            self._log_kyc_action(
                user_id=user_id,
                action="document_uploaded",
                kyc_document_id=kyc_document.id,
                kyc_verification_id=kyc_verification.id if kyc_verification else None,
                metadata={
                    "document_type": doc_type.value,
                    "file_size": file_size,
                    "file_hash": file_hash,
                },
            )

            return kyc_document.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to upload document: {e}")
            return {"error": "Failed to upload document"}

    def verify_document(
        self,
        document_id: int,
        verifier_id: int,
        status: str,
        rejection_reason: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Verify a KYC document"""
        try:
            document = KYCDocument.query.get(document_id)
            if not document:
                return {"error": "Document not found"}

            old_status = document.status

            # Update document status
            document.status = status
            document.verified_by = verifier_id
            document.verified_at = datetime.utcnow()
            document.rejection_reason = rejection_reason
            if extracted_data:
                document.extracted_data = extracted_data

            db.session.commit()

            # Log the action
            self._log_kyc_action(
                user_id=document.user_id,
                action="document_verified",
                kyc_document_id=document_id,
                performed_by=verifier_id,
                old_status=old_status,
                new_status=status,
                metadata={"rejection_reason": rejection_reason},
            )

            return document.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to verify document: {e}")
            return {"error": "Failed to verify document"}

    def upgrade_kyc_tier(
        self,
        user_id: int,
        new_tier: str,
        verifier_id: int,
        personal_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upgrade user's KYC tier"""
        try:
            kyc_verification = KYCVerification.query.filter_by(user_id=user_id).first()
            if not kyc_verification:
                return {"error": "KYC verification not found"}

            old_tier = kyc_verification.tier
            old_status = kyc_verification.status

            # Calculate risk score if personal data provided
            risk_score = None
            risk_level = None
            if personal_data:
                risk_score, risk_level = self._get_risk_score(personal_data)
                kyc_verification.risk_score = risk_score
                kyc_verification.risk_level = risk_level

                # Encrypt personal data
                if personal_data:
                    kyc_verification.encrypted_personal_data = (
                        self.encryption_service.encrypt(str(personal_data))
                    )

            # Update tier and limits
            kyc_verification.tier = new_tier
            kyc_verification.status = KYCStatus.APPROVED.value
            kyc_verification.verified_by = verifier_id
            kyc_verification.verified_at = datetime.utcnow()

            # Set limits based on tier
            if new_tier == KYCTier.TIER_1.value:
                kyc_verification.daily_limit = current_app.config.get(
                    "KYC_TIER_1_LIMIT", 100000
                )
                kyc_verification.monthly_limit = current_app.config.get(
                    "KYC_TIER_1_LIMIT", 100000
                )
                kyc_verification.yearly_limit = current_app.config.get(
                    "KYC_TIER_1_LIMIT", 100000
                )
            elif new_tier == KYCTier.TIER_2.value:
                kyc_verification.daily_limit = current_app.config.get(
                    "KYC_TIER_2_LIMIT", 1000000
                )
                kyc_verification.monthly_limit = current_app.config.get(
                    "KYC_TIER_2_LIMIT", 1000000
                )
                kyc_verification.yearly_limit = current_app.config.get(
                    "KYC_TIER_2_LIMIT", 1000000
                )

            db.session.commit()

            # Log the action
            self._log_kyc_action(
                user_id=user_id,
                action="kyc_tier_upgraded",
                kyc_verification_id=kyc_verification.id,
                performed_by=verifier_id,
                old_tier=old_tier,
                new_tier=new_tier,
                old_status=old_status,
                new_status=KYCStatus.APPROVED.value,
                metadata={
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "daily_limit": float(kyc_verification.daily_limit),
                    "monthly_limit": float(kyc_verification.monthly_limit),
                    "yearly_limit": float(kyc_verification.yearly_limit),
                },
            )

            return kyc_verification.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to upgrade KYC tier: {e}")
            return {"error": "Failed to upgrade KYC tier"}

    def get_user_kyc_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's KYC status and documents"""
        try:
            kyc_verification = KYCVerification.query.filter_by(user_id=user_id).first()
            if not kyc_verification:
                return {"error": "KYC verification not found"}

            documents = KYCDocument.query.filter_by(user_id=user_id).all()

            return {
                "verification": kyc_verification.to_dict(),
                "documents": [doc.to_dict() for doc in documents],
                "compliance_status": self._get_compliance_status(kyc_verification),
            }
        except Exception as e:
            logger.error(f"Failed to get KYC status: {e}")
            return {"error": "Failed to get KYC status"}

    def _get_compliance_status(
        self, kyc_verification: KYCVerification
    ) -> Dict[str, Any]:
        """Get compliance status for KYC verification"""
        return {
            "pep_checked": kyc_verification.pep_check,
            "sanctions_checked": kyc_verification.sanctions_check,
            "aml_checked": kyc_verification.aml_check,
            "risk_score": kyc_verification.risk_score,
            "risk_level": kyc_verification.risk_level,
            "compliance_score": self._calculate_compliance_score(kyc_verification),
        }

    def _calculate_compliance_score(self, kyc_verification: KYCVerification) -> float:
        """Calculate overall compliance score"""
        score = 0.0

        # Base score for verification status
        if kyc_verification.status == KYCStatus.APPROVED.value:
            score += 50

        # Tier bonus
        if kyc_verification.tier == KYCTier.TIER_1.value:
            score += 25
        elif kyc_verification.tier == KYCTier.TIER_2.value:
            score += 40

        # Compliance checks
        if kyc_verification.pep_check:
            score += 10
        if kyc_verification.sanctions_check:
            score += 10
        if kyc_verification.aml_check:
            score += 10

        # Risk penalty
        if kyc_verification.risk_score:
            score -= kyc_verification.risk_score * 0.3

        return max(0, min(100, score))

    def _log_kyc_action(
        self,
        user_id: int,
        action: str,
        performed_by: Optional[int] = None,
        kyc_verification_id: Optional[int] = None,
        kyc_document_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        old_tier: Optional[str] = None,
        new_tier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ):
        """Log KYC action for audit trail"""
        try:
            audit_log = KYCAuditLog(
                user_id=user_id,
                action=action,
                kyc_verification_id=kyc_verification_id,
                kyc_document_id=kyc_document_id,
                performed_by=performed_by,
                old_status=old_status,
                new_status=new_status,
                old_tier=old_tier,
                new_tier=new_tier,
                metadata=metadata,
                notes=notes,
            )

            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log KYC action: {e}")

    def get_kyc_audit_trail(
        self, user_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get KYC audit trail for a user"""
        try:
            audit_logs = (
                KYCAuditLog.query.filter_by(user_id=user_id)
                .order_by(KYCAuditLog.created_at.desc())
                .limit(limit)
                .all()
            )

            return [log.to_dict() for log in audit_logs]
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []

    def check_transaction_limits(
        self, user_id: int, amount: float, transaction_type: str = "transfer"
    ) -> Dict[str, Any]:
        """Check if transaction is within KYC limits"""
        try:
            kyc_verification = KYCVerification.query.filter_by(user_id=user_id).first()
            if not kyc_verification:
                return {
                    "allowed": False,
                    "reason": "KYC verification required",
                    "required_tier": KYCTier.TIER_0.value,
                }

            # Check if verification is approved
            if kyc_verification.status != KYCStatus.APPROVED.value:
                return {
                    "allowed": False,
                    "reason": "KYC verification pending",
                    "current_status": kyc_verification.status,
                }

            # Check limits based on transaction type
            if transaction_type == "daily":
                limit = kyc_verification.daily_limit
            elif transaction_type == "monthly":
                limit = kyc_verification.monthly_limit
            elif transaction_type == "yearly":
                limit = kyc_verification.yearly_limit
            else:
                limit = kyc_verification.daily_limit  # Default to daily

            if amount > limit:
                return {
                    "allowed": False,
                    "reason": f"Amount exceeds {transaction_type} limit",
                    "limit": float(limit),
                    "current_tier": kyc_verification.tier,
                    "required_tier": self._get_required_tier_for_amount(amount),
                }

            return {
                "allowed": True,
                "current_tier": kyc_verification.tier,
                "limit": float(limit),
            }
        except Exception as e:
            logger.error(f"Failed to check transaction limits: {e}")
            return {"allowed": False, "reason": "Error checking limits"}

    def _get_required_tier_for_amount(self, amount: float) -> str:
        """Determine required KYC tier for transaction amount"""
        if amount <= current_app.config.get("KYC_TIER_0_LIMIT", 10000):
            return KYCTier.TIER_0.value
        elif amount <= current_app.config.get("KYC_TIER_1_LIMIT", 100000):
            return KYCTier.TIER_1.value
        else:
            return KYCTier.TIER_2.value
