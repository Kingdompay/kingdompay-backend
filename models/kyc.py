"""
KYC (Know Your Customer) Models for KingdomPay
Handles user verification and compliance requirements
"""

from datetime import datetime
from enum import Enum
from extensions import db
from sqlalchemy import Index, CheckConstraint
import uuid

# Use the shared SQLAlchemy instance from extensions


class KYCStatus(Enum):
    """KYC verification status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNDER_REVIEW = "under_review"


class KYCTier(Enum):
    """KYC verification tiers"""

    TIER_0 = "tier_0"  # Phone verified only
    TIER_1 = "tier_1"  # Basic ID verification
    TIER_2 = "tier_2"  # Enhanced verification


class DocumentType(Enum):
    """Supported document types"""

    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    EMPLOYMENT_LETTER = "employment_letter"


class KYCDocument(db.Model):
    """KYC document storage"""

    __tablename__ = "kyc_documents"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # Use string to match DB CHECK constraint
    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hash
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)

    # Verification fields
    status = db.Column(db.String(20), default=KYCStatus.PENDING.value, nullable=False)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # OCR and extraction data
    extracted_data = db.Column(db.JSON, nullable=True)  # OCR extracted information
    confidence_score = db.Column(db.Float, nullable=True)  # OCR confidence

    # Metadata
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="kyc_documents")
    verifier = db.relationship(
        "User", foreign_keys=[verified_by], backref="verified_documents"
    )

    # Indexes
    __table_args__ = (
        Index("idx_kyc_documents_user_id", "user_id"),
        Index("idx_kyc_documents_status", "status"),
        Index("idx_kyc_documents_type", "document_type"),
        Index("idx_kyc_documents_hash", "file_hash"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "document_type": self.document_type,
            "status": self.status,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "rejection_reason": self.rejection_reason,
            "confidence_score": self.confidence_score,
        }


class KYCVerification(db.Model):
    """KYC verification records"""

    __tablename__ = "kyc_verifications"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )

    # Verification tier and status (stored as string values to match DB CHECK constraints)
    tier = db.Column(db.String(20), default=KYCTier.TIER_0.value, nullable=False)
    status = db.Column(db.String(20), default=KYCStatus.PENDING.value, nullable=False)

    # Personal information (encrypted)
    encrypted_personal_data = db.Column(db.Text, nullable=True)

    # Verification limits
    daily_limit = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    monthly_limit = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    yearly_limit = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # Verification metadata
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Compliance flags
    pep_check = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Politically Exposed Person
    sanctions_check = db.Column(db.Boolean, default=False, nullable=False)
    aml_check = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Anti-Money Laundering

    # Risk assessment
    risk_score = db.Column(db.Float, nullable=True)  # 0-100 risk score
    risk_level = db.Column(db.String(20), nullable=True)  # low, medium, high

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="kyc_verification")
    verifier = db.relationship(
        "User", foreign_keys=[verified_by], backref="verified_kycs"
    )

    # Indexes
    __table_args__ = (
        Index("idx_kyc_verifications_user_id", "user_id"),
        Index("idx_kyc_verifications_status", "status"),
        Index("idx_kyc_verifications_tier", "tier"),
        Index("idx_kyc_verifications_risk_score", "risk_score"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "tier": self.tier,
            "status": self.status,
            "daily_limit": float(self.daily_limit),
            "monthly_limit": float(self.monthly_limit),
            "yearly_limit": float(self.yearly_limit),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "rejection_reason": self.rejection_reason,
            "pep_check": self.pep_check,
            "sanctions_check": self.sanctions_check,
            "aml_check": self.aml_check,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class KYCAuditLog(db.Model):
    """KYC audit trail for compliance"""

    __tablename__ = "kyc_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # Related entities
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kyc_verification_id = db.Column(
        db.Integer, db.ForeignKey("kyc_verifications.id"), nullable=True
    )
    kyc_document_id = db.Column(
        db.Integer, db.ForeignKey("kyc_documents.id"), nullable=True
    )

    # Action details
    action = db.Column(
        db.String(100), nullable=False
    )  # e.g., "document_uploaded", "verification_approved"
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=True)
    old_tier = db.Column(db.String(50), nullable=True)
    new_tier = db.Column(db.String(50), nullable=True)

    # Actor information
    performed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    # Additional data
    audit_metadata = db.Column(db.JSON, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="kyc_audit_logs")
    kyc_verification = db.relationship("KYCVerification", backref="audit_logs")
    kyc_document = db.relationship("KYCDocument", backref="audit_logs")
    performer = db.relationship(
        "User", foreign_keys=[performed_by], backref="performed_kyc_actions"
    )

    # Indexes
    __table_args__ = (
        Index("idx_kyc_audit_logs_user_id", "user_id"),
        Index("idx_kyc_audit_logs_action", "action"),
        Index("idx_kyc_audit_logs_created_at", "created_at"),
        Index("idx_kyc_audit_logs_performed_by", "performed_by"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "kyc_verification_id": self.kyc_verification_id,
            "kyc_document_id": self.kyc_document_id,
            "action": self.action,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "old_tier": self.old_tier,
            "new_tier": self.new_tier,
            "performed_by": self.performed_by,
            "ip_address": self.ip_address,
            "audit_metadata": self.audit_metadata,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
