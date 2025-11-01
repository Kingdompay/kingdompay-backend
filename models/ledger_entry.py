"""
LedgerEntry model for KingdomPay
"""

from datetime import datetime
from extensions import db


class LedgerEntry(db.Model):
    """Double-entry line item for a wallet/account posting"""

    __tablename__ = "ledger_entries"

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(
        db.Integer,
        db.ForeignKey("ledger_journals.id", ondelete="CASCADE"),
        nullable=False,
    )
    wallet_id = db.Column(
        db.Integer, db.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    account_code = db.Column(db.String(50), nullable=False)
    debit = db.Column(db.Numeric(15, 2), default=0.00, nullable=False)
    credit = db.Column(db.Numeric(15, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="KES")
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<LedgerEntry J{self.journal_id} W{self.wallet_id} D{self.debit} C{self.credit}>"
