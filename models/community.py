"""
Community and CommunityMember models for KingdomPay
"""

from datetime import datetime
from enum import Enum
from extensions import db
from sqlalchemy import Index
import uuid


class CommunityType(str, Enum):
    CHURCH = "CHURCH"
    CLAN = "CLAN"
    SACCO = "SACCO"
    NGO = "NGO"
    OTHER = "OTHER"


class CommunityRole(str, Enum):
    ADMIN = "ADMIN"
    TREASURER = "TREASURER"
    MEMBER = "MEMBER"


class Community(db.Model):
    __tablename__ = "communities"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, default=CommunityType.OTHER.value)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    owner_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    settings_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    contributions = db.relationship("Contribution", back_populates="community")

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "slug": self.slug,
            "owner_user_id": self.owner_user_id,
            "settings_json": self.settings_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CommunityMember(db.Model):
    __tablename__ = "community_members"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(
        db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = db.Column(db.String(20), nullable=False, default=CommunityRole.MEMBER.value)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="community_memberships")
    community = db.relationship("Community", backref="members")

    __table_args__ = (
        db.UniqueConstraint("community_id", "user_id", name="uq_community_member"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "community_id": self.community_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Contribution(db.Model):
    """Contributions made by users to communities"""

    __tablename__ = "contributions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    community_id = db.Column(
        db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    contribution_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'monthly', 'one-time', 'emergency'
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="contributions")
    community = db.relationship("Community", back_populates="contributions")

    # Indexes
    __table_args__ = (
        Index("idx_contributions_user_id", "user_id"),
        Index("idx_contributions_community_id", "community_id"),
        Index("idx_contributions_created_at", "created_at"),
        Index("idx_contributions_type", "contribution_type"),
    )

    def __repr__(self):
        return f"<Contribution {self.amount} by {self.user_id} to {self.community_id}>"

    def to_dict(self):
        """Convert contribution to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "community_id": self.community_id,
            "amount": float(self.amount),
            "contribution_type": self.contribution_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_user_contributions(cls, user_id, limit=50, offset=0):
        """Get contributions made by a user"""
        return (
            cls.query.filter_by(user_id=user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @classmethod
    def get_community_contributions(cls, community_id, limit=50, offset=0):
        """Get contributions to a community"""
        return (
            cls.query.filter_by(community_id=community_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @classmethod
    def get_total_contributions(cls, community_id):
        """Get total amount contributed to a community"""
        from sqlalchemy import func

        result = (
            cls.query.with_entities(func.sum(cls.amount))
            .filter_by(community_id=community_id)
            .scalar()
        )
        return float(result) if result else 0.0
