"""
OTP verification model for KingdomPay
"""

from datetime import datetime, timedelta, timezone
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string


class OTPVerification(db.Model):
    """OTP verification model for phone number verification"""

    __tablename__ = "otp_verifications"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    # Store OTP as a password-style hash to avoid plaintext at rest
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<OTPVerification {self.phone_number}>"

    @classmethod
    def generate_otp(cls, phone_number, expiry_minutes=5):
        """Generate a new OTP for phone number"""
        # Generate 6-digit OTP
        otp_code = "".join(random.choices(string.digits, k=6))

        # Set expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

        # Create OTP record
        otp = cls(
            phone_number=phone_number,
            otp_hash=generate_password_hash(otp_code),
            expires_at=expires_at,
        )

        db.session.add(otp)
        db.session.commit()

        # Add the otp_code as an attribute for immediate use (before hashing)
        # This is only for testing purposes - the actual OTP is hashed
        otp.otp_code = otp_code
        return otp

    @classmethod
    def verify_otp(cls, phone_number, otp_code):
        """Verify OTP code for phone number"""
        # Find valid OTP
        otp = (
            cls.query.filter(
                cls.phone_number == phone_number,
                cls.is_used == False,
                cls.expires_at > datetime.now(timezone.utc),
            )
            .order_by(cls.created_at.desc())
            .first()
        )

        if not otp or not check_password_hash(otp.otp_hash, otp_code):
            # Increment attempts for any OTP for this phone number
            cls.query.filter(
                cls.phone_number == phone_number, cls.is_used == False
            ).update({"attempts": cls.attempts + 1})
            db.session.commit()
            return False

        # Mark as used
        otp.is_used = True
        db.session.commit()

        return True

    @classmethod
    def cleanup_expired(cls):
        """Clean up expired OTPs"""
        expired_count = cls.query.filter(
            cls.expires_at < datetime.now(timezone.utc)
        ).delete()
        db.session.commit()
        return expired_count

    @classmethod
    def get_recent_attempts(cls, phone_number, minutes=5):
        """Get recent OTP attempts for rate limiting"""
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.phone_number == phone_number, cls.created_at >= since
        ).count()

    def is_expired(self):
        """Check if OTP is expired"""
        return datetime.utcnow() > self.expires_at

    @classmethod
    def get_latest_otp_code(cls, phone_number):
        """Get the latest OTP code for a phone number (for testing purposes only)"""
        # This method is only for testing - in production, OTP codes should never be retrievable
        otp = (
            cls.query.filter(
                cls.phone_number == phone_number,
                cls.is_used == False,
                cls.expires_at > datetime.now(timezone.utc),
            )
            .order_by(cls.created_at.desc())
            .first()
        )

        if otp and hasattr(otp, "otp_code"):
            return otp.otp_code
        return None
