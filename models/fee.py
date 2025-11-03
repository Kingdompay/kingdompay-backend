"""
Fee models for transaction fees and community contributions
"""

from datetime import datetime
from decimal import Decimal
from extensions import db


class TransactionFee(db.Model):
    """Transaction fee record - tracks fee allocation"""
    __tablename__ = "transaction_fees"

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey("ledger_journals.id", ondelete="CASCADE"), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="SET NULL"))
    transaction_amount = db.Column(db.Numeric(15, 2), nullable=False)
    fee_amount = db.Column(db.Numeric(15, 2), nullable=False)  # Total 1.5%
    platform_fee = db.Column(db.Numeric(15, 2), nullable=False)  # 0.5%
    community_fee = db.Column(db.Numeric(15, 2), nullable=False)  # 0.5%
    federal_fee = db.Column(db.Numeric(15, 2), nullable=False)  # 0.5%
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "journal_id": self.journal_id,
            "payment_id": self.payment_id,
            "transaction_amount": float(self.transaction_amount),
            "fee_amount": float(self.fee_amount),
            "platform_fee": float(self.platform_fee),
            "community_fee": float(self.community_fee),
            "federal_fee": float(self.federal_fee),
            "community_id": self.community_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CommunityContribution(db.Model):
    """Community Development Fund contribution (1% default)"""
    __tablename__ = "community_contributions"

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey("ledger_journals.id", ondelete="CASCADE"), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="SET NULL"))
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    transaction_amount = db.Column(db.Numeric(15, 2), nullable=False)
    contribution_amount = db.Column(db.Numeric(15, 2), nullable=False)  # 1% default
    contribution_rate = db.Column(db.Numeric(5, 4), nullable=False, default=Decimal("0.01"))  # Configurable per community
    allocated_to = db.Column(db.String(50))  # EDUCATION|HEALTH|WELFARE|GENERAL
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "journal_id": self.journal_id,
            "payment_id": self.payment_id,
            "community_id": self.community_id,
            "transaction_amount": float(self.transaction_amount),
            "contribution_amount": float(self.contribution_amount),
            "contribution_rate": float(self.contribution_rate),
            "allocated_to": self.allocated_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CommunityDevelopmentFund(db.Model):
    """Community Development Fund balances and allocations"""
    __tablename__ = "community_development_funds"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, unique=True)
    education_balance = db.Column(db.Numeric(15, 2), default=Decimal("0"))
    health_balance = db.Column(db.Numeric(15, 2), default=Decimal("0"))
    welfare_balance = db.Column(db.Numeric(15, 2), default=Decimal("0"))
    general_balance = db.Column(db.Numeric(15, 2), default=Decimal("0"))
    contribution_rate = db.Column(db.Numeric(5, 4), default=Decimal("0.01"))  # 1% default, configurable
    total_contributed = db.Column(db.Numeric(15, 2), default=Decimal("0"))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "community_id": self.community_id,
            "education_balance": float(self.education_balance),
            "health_balance": float(self.health_balance),
            "welfare_balance": float(self.welfare_balance),
            "general_balance": float(self.general_balance),
            "contribution_rate": float(self.contribution_rate),
            "total_contributed": float(self.total_contributed),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

