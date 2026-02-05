"""
Savings Goal model for KingdomPay
"""

from datetime import datetime, timezone
from extensions import db
from decimal import Decimal


class SavingsGoal(db.Model):
    """Savings Goal model for user savings targets"""

    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    target_amount = db.Column(db.Numeric(15, 2), nullable=False)
    current_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    currency = db.Column(db.String(3), default="KES", nullable=False)
    icon = db.Column(db.String(50), default="savings")
    deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(
        db.String(20), default="active", nullable=False
    )  # active, completed, cancelled
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = db.relationship("User", backref="savings_goals")

    def __repr__(self):
        return f"<SavingsGoal {self.id}: {self.name}>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "target_amount": float(self.target_amount),
            "current_amount": float(self.current_amount),
            "currency": self.currency,
            "icon": self.icon,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "progress_percentage": min(
                100, (float(self.current_amount) / float(self.target_amount) * 100)
            )
            if self.target_amount > 0
            else 0,
        }

    def is_completed(self):
        """Check if goal is completed"""
        return self.current_amount >= self.target_amount

    def update_status(self):
        """Update status based on current amount"""
        if self.is_completed() and self.status == "active":
            self.status = "completed"
            self.updated_at = datetime.utcnow()
            db.session.commit()
