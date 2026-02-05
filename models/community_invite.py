"""
CommunityInvite model for invite/join flows
"""

from datetime import datetime, timedelta
import secrets
from extensions import db


class CommunityInvite(db.Model):
    __tablename__ = "community_invites"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(
        db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    inviter_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    def create_invite(
        cls, community_id: int, inviter_user_id: int, ttl_minutes: int = 1440
    ):
        token = secrets.token_urlsafe(24)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        invite = cls(
            community_id=community_id,
            inviter_user_id=inviter_user_id,
            token=token,
            expires_at=expires_at,
            status="ACTIVE",
        )
        db.session.add(invite)
        db.session.commit()
        # Return the invite - attributes should be accessible immediately after commit
        # The route handler will access them right away to avoid any lazy loading issues
        return invite

    @classmethod
    def validate_token(cls, token: str):
        invite = cls.query.filter_by(token=token, status="ACTIVE").first()
        if not invite:
            return None
        if invite.expires_at <= datetime.utcnow():
            return None
        return invite
