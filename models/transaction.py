"""
Transaction model for KingdomPay
"""

from datetime import datetime
from extensions import db
import random
from decimal import Decimal


class Transaction(db.Model):
    """Transaction model for recording all money movements"""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    source_wallet_id = db.Column(
        db.Integer, db.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True
    )
    destination_wallet_id = db.Column(
        db.Integer, db.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=True
    )
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    source_balance_after = db.Column(db.Numeric(15, 2))
    destination_balance_after = db.Column(db.Numeric(15, 2))
    reference_number = db.Column(
        db.String(30),
        unique=True,
        default=lambda: f"TX-{random.randint(100000000000, 999999999999)}",
    )
    status = db.Column(db.String(20), default="SUCCESS")
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.reference_number}>"

    def to_dict(self):
        """Convert transaction to dictionary for API responses"""
        return {
            "id": self.id,
            "source_wallet_id": self.source_wallet_id,
            "destination_wallet_id": self.destination_wallet_id,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount),
            "source_balance_after": (
                float(self.source_balance_after) if self.source_balance_after else None
            ),
            "destination_balance_after": (
                float(self.destination_balance_after)
                if self.destination_balance_after
                else None
            ),
            "reference_number": self.reference_number,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_user_transactions(cls, user_id, limit=50, offset=0):
        """Get transactions for a user (both sent and received)"""
        from models.wallet import Wallet

        return (
            cls.query.filter(
                (
                    cls.source_wallet_id.in_(
                        db.session.query(Wallet.id).filter_by(user_id=user_id)
                    )
                )
                | (
                    cls.destination_wallet_id.in_(
                        db.session.query(Wallet.id).filter_by(user_id=user_id)
                    )
                )
            )
            .order_by(cls.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @classmethod
    def get_wallet_transactions(cls, wallet_id, limit=50, offset=0):
        """Get transactions for a specific wallet"""
        return (
            cls.query.filter(
                (cls.source_wallet_id == wallet_id)
                | (cls.destination_wallet_id == wallet_id)
            )
            .order_by(cls.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
