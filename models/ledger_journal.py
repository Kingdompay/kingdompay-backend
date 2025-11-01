"""
LedgerJournal model for KingdomPay
"""

from datetime import datetime
from extensions import db


class LedgerJournal(db.Model):
    """Journal groups balanced ledger entries for a single logical transaction"""

    __tablename__ = "ledger_journals"

    id = db.Column(db.Integer, primary_key=True)
    external_ref = db.Column(db.String(100), index=True)
    idempotency_key = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    entries = db.relationship(
        "LedgerEntry",
        backref="journal",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return f"<LedgerJournal {self.id} {self.idempotency_key}>"
