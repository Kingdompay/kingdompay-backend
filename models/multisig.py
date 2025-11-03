"""
Multi-signature approval models for community wallet operations
"""

from datetime import datetime
from extensions import db


class MultiSigApproval(db.Model):
    """Multi-signature approval requests for community wallet operations"""
    __tablename__ = "multisig_approvals"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False)  # WITHDRAWAL|PAYOUT|DISBURSEMENT
    operation_ref = db.Column(db.String(200))  # payment_id, payout_id, etc.
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default="KES")
    destination = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="PENDING")  # PENDING|APPROVED|REJECTED|CANCELLED
    required_signatures = db.Column(db.Integer, default=2)  # 2 of N (typically 3-5 admins)
    approval_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    approved_at = db.Column(db.DateTime(timezone=True))
    executed_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self):
        return {
            "id": self.id,
            "community_id": self.community_id,
            "operation_type": self.operation_type,
            "operation_ref": self.operation_ref,
            "amount": float(self.amount),
            "currency": self.currency,
            "destination": self.destination,
            "description": self.description,
            "status": self.status,
            "required_signatures": self.required_signatures,
            "approval_count": self.approval_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


class MultiSigSignature(db.Model):
    """Individual signatures for multi-sig approvals"""
    __tablename__ = "multisig_signatures"

    id = db.Column(db.Integer, primary_key=True)
    approval_id = db.Column(db.Integer, db.ForeignKey("multisig_approvals.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    signature_type = db.Column(db.String(20), nullable=False)  # APPROVE|REJECT
    signed_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))

    def to_dict(self):
        return {
            "id": self.id,
            "approval_id": self.approval_id,
            "user_id": self.user_id,
            "signature_type": self.signature_type,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
        }

