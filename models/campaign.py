"""
Campaign model for KingdomPay
"""

from datetime import datetime
from extensions import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(
        db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # TITHES|OFFERING|DONATION|PROJECT
    target_amount = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "community_id": self.community_id,
            "title": self.title,
            "type": self.type,
            "target_amount": float(self.target_amount) if self.target_amount else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
