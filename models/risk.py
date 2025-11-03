"""
Risk and AML models for Phase 2
"""

from datetime import datetime
from extensions import db


class Blacklist(db.Model):
    __tablename__ = "blacklists"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False)  # PHONE|EMAIL|WALLET|USER
    entity_value = db.Column(db.String(200), nullable=False, index=True)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


class AMLCase(db.Model):
    __tablename__ = "aml_cases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    case_type = db.Column(db.String(50))  # STRUCTURING|HIGH_RISK|SANCTIONS|etc
    status = db.Column(db.String(20), default="OPEN")  # OPEN|INVESTIGATING|RESOLVED|CLOSED
    details_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True))

