"""
User model for KingdomPay
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    """User model for authentication and profile management"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Optional for OTP-only auth
    is_phone_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime(timezone=True))
    reset_token = db.Column(db.String(255))
    reset_token_expires = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    wallet = db.relationship(
        "Wallet", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.phone_number}>"

    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        if not self.password:
            return False
        return check_password_hash(self.password, password)

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone_number": self.phone_number,
            "is_phone_verified": self.is_phone_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def find_by_phone(cls, phone_number):
        """Find user by phone number"""
        return cls.query.filter_by(phone_number=phone_number).first()

    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        return cls.query.filter_by(email=email).first()

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()
