"""
Webhook registration and event models
"""

from datetime import datetime
from extensions import db


class Webhook(db.Model):
    __tablename__ = "webhooks"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(
        db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE")
    )
    url = db.Column(db.String(300), nullable=False)
    secret = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


class WebhookEvent(db.Model):
    __tablename__ = "webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    delivered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
