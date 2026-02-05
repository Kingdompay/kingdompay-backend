"""
Money Request model for KingdomPay
"""

from datetime import datetime, timezone
from extensions import db
from decimal import Decimal


class MoneyRequest(db.Model):
    """Money Request model for requesting money from other users"""

    __tablename__ = "money_requests"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default="KES", nullable=False)
    message = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default="general")
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(
        db.String(20), default="pending", nullable=False, index=True
    )  # pending, accepted, rejected, cancelled, expired
    transaction_id = db.Column(
        db.Integer, db.ForeignKey("transactions.id"), nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    responded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    requester = db.relationship(
        "User", foreign_keys=[requester_id], backref="money_requests_sent"
    )
    recipient = db.relationship(
        "User", foreign_keys=[recipient_id], backref="money_requests_received"
    )
    transaction = db.relationship("Transaction", backref="money_request")

    def __repr__(self):
        return f"<MoneyRequest {self.id}: {self.requester_id} -> {self.recipient_id}>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "requester_id": self.requester_id,
            "recipient_id": self.recipient_id,
            "requester_name": self.requester.full_name if self.requester else None,
            "recipient_name": self.recipient.full_name if self.recipient else None,
            "amount": float(self.amount),
            "currency": self.currency,
            "message": self.message,
            "category": self.category,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }

    def is_expired(self):
        """Check if request has expired"""
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date

    def can_be_responded_to(self):
        """Check if request can still be responded to"""
        return self.status == "pending" and not self.is_expired()
