"""
Wallet model for KingdomPay
"""

from datetime import datetime, timezone
from extensions import db
import uuid
import random
from decimal import Decimal


class Wallet(db.Model):
    """Wallet model for storing user funds"""

    __tablename__ = "wallets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    wallet_number = db.Column(
        db.String(36), unique=True, default=lambda: str(uuid.uuid4())
    )
    display_number = db.Column(db.String(20), unique=True)
    balance = db.Column(db.Numeric(15, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="KES")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    transactions_sent = db.relationship(
        "Transaction",
        foreign_keys="Transaction.source_wallet_id",
        backref="source_wallet",
    )
    transactions_received = db.relationship(
        "Transaction",
        foreign_keys="Transaction.destination_wallet_id",
        backref="destination_wallet",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.display_number:
            self.display_number = f"WAL-{random.randint(100000000, 999999999)}"

    def __repr__(self):
        return f"<Wallet {self.display_number}>"

    def to_dict(self):
        """Convert wallet to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "wallet_number": self.wallet_number,
            "display_number": self.display_number,
            "balance": float(self.balance),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def can_afford(self, amount):
        """Check if wallet has sufficient balance"""
        return float(self.balance) >= float(amount)

    def add_funds(self, amount, description="Deposit"):
        """Add funds to wallet"""
        from models.transaction import Transaction

        # Convert amount to Decimal to ensure type consistency
        amount = Decimal(str(amount))
        self.balance += amount
        self.updated_at = datetime.now(timezone.utc)

        # Create transaction record
        transaction = Transaction(
            destination_wallet_id=self.id,
            transaction_type="DEPOSIT",
            amount=amount,
            destination_balance_after=self.balance,
            description=description,
            status="SUCCESS",
        )

        db.session.add(transaction)
        db.session.commit()

        return transaction

    def deduct_funds(self, amount, description="Withdrawal"):
        """Deduct funds from wallet"""
        from models.transaction import Transaction

        # Convert amount to Decimal to ensure type consistency
        amount = Decimal(str(amount))

        if not self.can_afford(amount):
            raise ValueError("Insufficient funds")

        self.balance -= amount
        self.updated_at = datetime.now(timezone.utc)

        # Create transaction record
        transaction = Transaction(
            source_wallet_id=self.id,
            transaction_type="WITHDRAWAL",
            amount=amount,
            source_balance_after=self.balance,
            description=description,
            status="SUCCESS",
        )

        db.session.add(transaction)
        db.session.commit()

        return transaction

    @classmethod
    def find_by_user_id(cls, user_id):
        """Find wallet by user ID"""
        return cls.query.filter_by(user_id=user_id).first()

    @classmethod
    def find_by_display_number(cls, display_number):
        """Find wallet by display number"""
        return cls.query.filter_by(display_number=display_number).first()
