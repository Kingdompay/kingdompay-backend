"""
Payment model for external provider transactions
"""

from datetime import datetime
from extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    payer_wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id", ondelete="SET NULL"))
    payee_wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id", ondelete="SET NULL"))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="KES")
    status = db.Column(db.String(20), default="PENDING")  # PENDING|SUCCESS|FAILED|CANCELLED
    method = db.Column(db.String(20), nullable=False, default="MOMO")  # WALLET|MOMO|CARD|BANK
    provider = db.Column(db.String(50))  # MPESA|AIRTEL|TKASH|FLUTTERWAVE|etc
    provider_ref = db.Column(db.String(200), index=True)
    provider_transaction_id = db.Column(db.String(200))  # M-Pesa receipt number
    payer_phone = db.Column(db.String(20))  # Phone number for M-Pesa
    failure_reason = db.Column(db.String(500))  # Reason for failure
    journal_id = db.Column(db.Integer, db.ForeignKey("ledger_journals.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "payer_wallet_id": self.payer_wallet_id,
            "payee_wallet_id": self.payee_wallet_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status,
            "method": self.method,
            "provider": self.provider,
            "provider_ref": self.provider_ref,
            "provider_transaction_id": self.provider_transaction_id,
            "payer_phone": self.payer_phone,
            "failure_reason": self.failure_reason,
            "journal_id": self.journal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

