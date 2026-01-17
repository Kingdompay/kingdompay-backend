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
    role = db.Column(
        db.String(20), default="USER", nullable=False
    )  # USER|ADMIN|SUPPORT
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
    community_memberships = db.relationship(
        "CommunityMember", back_populates="user", cascade="all, delete-orphan"
    )
    contributions = db.relationship(
        "Contribution", back_populates="user", cascade="all, delete-orphan"
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
        # Get KYC status if available
        from models.kyc import KYCVerification

        kyc_verification = KYCVerification.query.filter_by(user_id=self.id).first()
        kyc_status = kyc_verification.status if kyc_verification else None
        kyc_tier = kyc_verification.tier if kyc_verification else None

        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone_number": self.phone_number,
            "is_phone_verified": self.is_phone_verified,
            "is_active": self.is_active,
            "role": self.role,
            "kyc_status": kyc_status,
            "kyc_tier": kyc_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_admin(self):
        """Check if user is an admin"""
        return self.role == "ADMIN"

    def is_support(self):
        """Check if user is support staff"""
        return self.role in ("ADMIN", "SUPPORT")

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
