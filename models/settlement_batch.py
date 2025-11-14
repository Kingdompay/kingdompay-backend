"""
Settlement batch model for reconciliation
"""

from datetime import datetime
from extensions import db


class SettlementBatch(db.Model):
    __tablename__ = "settlement_batches"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    settlement_date = db.Column(db.Date, nullable=False)
    expected_amount = db.Column(db.Numeric(15, 2), nullable=False)
    actual_amount = db.Column(db.Numeric(15, 2))
    variance_json = db.Column(db.JSON)
    status = db.Column(db.String(20), default="PENDING")  # PENDING|RECONCILED|VARIANCE
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "expected_amount": float(self.expected_amount),
            "actual_amount": float(self.actual_amount) if self.actual_amount else None,
            "variance_json": self.variance_json,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

