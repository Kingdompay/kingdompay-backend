"""
Two-Factor Authentication Service for KingdomPay
Handles TOTP-based 2FA setup and verification
"""

import os
import pyotp
import qrcode
import io
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from extensions import db

logger = logging.getLogger(__name__)


class TwoFactorAuth(db.Model):
    """Two-Factor Authentication settings model"""
    __tablename__ = "two_factor_auth"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    secret = db.Column(db.String(32), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.JSON)  # Encrypted backup codes
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    verified_at = db.Column(db.DateTime(timezone=True))  # When 2FA was first verified

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


class TwoFactorService:
    """Service for managing two-factor authentication"""

    def __init__(self):
        self.issuer_name = os.environ.get("APP_NAME", "KingdomPay")

    def setup_2fa(self, user_id: int, user_email: str = None) -> Dict[str, Any]:
        """
        Setup 2FA for a user - generates secret and QR code
        """
        try:
            # Check if already exists
            existing = TwoFactorAuth.query.filter_by(user_id=user_id).first()
            if existing and existing.is_enabled:
                return {"error": "2FA is already enabled. Disable first to reconfigure."}

            # Generate new secret
            secret = pyotp.random_base32()
            
            # Create or update record
            if existing:
                existing.secret = secret
                existing.is_enabled = False
                existing.verified_at = None
            else:
                tfa = TwoFactorAuth(user_id=user_id, secret=secret)
                db.session.add(tfa)
            
            db.session.commit()

            # Generate TOTP URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user_email or f"user_{user_id}",
                issuer_name=self.issuer_name
            )

            # Generate QR code
            qr_code_base64 = self._generate_qr_code(provisioning_uri)

            # Generate backup codes
            backup_codes = self._generate_backup_codes()

            return {
                "success": True,
                "secret": secret,
                "qr_code": qr_code_base64,
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes,
                "message": "Scan the QR code with your authenticator app, then verify with a code"
            }

        except Exception as e:
            logger.error(f"Failed to setup 2FA: {e}")
            db.session.rollback()
            return {"error": str(e)}

    def verify_and_enable(self, user_id: int, code: str) -> Dict[str, Any]:
        """
        Verify 2FA code and enable 2FA for user
        """
        try:
            tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
            if not tfa:
                return {"error": "2FA not set up. Call setup endpoint first."}

            if tfa.is_enabled:
                return {"error": "2FA is already enabled"}

            # Verify the code
            totp = pyotp.TOTP(tfa.secret)
            if not totp.verify(code, valid_window=1):
                return {"error": "Invalid verification code"}

            # Enable 2FA
            tfa.is_enabled = True
            tfa.verified_at = datetime.utcnow()
            
            # Generate and store backup codes
            backup_codes = self._generate_backup_codes()
            tfa.backup_codes = self._hash_backup_codes(backup_codes)
            
            db.session.commit()

            return {
                "success": True,
                "message": "2FA has been enabled successfully",
                "backup_codes": backup_codes,
                "warning": "Save these backup codes securely. They can only be shown once."
            }

        except Exception as e:
            logger.error(f"Failed to verify 2FA: {e}")
            return {"error": str(e)}

    def verify_code(self, user_id: int, code: str) -> Dict[str, Any]:
        """
        Verify a 2FA code during login
        """
        try:
            tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
            if not tfa or not tfa.is_enabled:
                return {"valid": True, "2fa_required": False}  # 2FA not enabled

            # Check if it's a backup code
            if len(code) == 8 and self._verify_backup_code(tfa, code):
                return {"valid": True, "used_backup_code": True}

            # Verify TOTP code
            totp = pyotp.TOTP(tfa.secret)
            if totp.verify(code, valid_window=1):
                return {"valid": True}
            else:
                return {"valid": False, "error": "Invalid 2FA code"}

        except Exception as e:
            logger.error(f"Failed to verify 2FA code: {e}")
            return {"valid": False, "error": str(e)}

    def is_2fa_enabled(self, user_id: int) -> bool:
        """Check if 2FA is enabled for user"""
        tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
        return tfa.is_enabled if tfa else False

    def disable_2fa(self, user_id: int, code: str) -> Dict[str, Any]:
        """
        Disable 2FA for user (requires valid code)
        """
        try:
            tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
            if not tfa or not tfa.is_enabled:
                return {"error": "2FA is not enabled"}

            # Verify the code first
            totp = pyotp.TOTP(tfa.secret)
            if not totp.verify(code, valid_window=1):
                # Check backup codes
                if not self._verify_backup_code(tfa, code):
                    return {"error": "Invalid verification code"}

            # Disable 2FA
            tfa.is_enabled = False
            tfa.backup_codes = None
            db.session.commit()

            return {"success": True, "message": "2FA has been disabled"}

        except Exception as e:
            logger.error(f"Failed to disable 2FA: {e}")
            return {"error": str(e)}

    def get_2fa_status(self, user_id: int) -> Dict[str, Any]:
        """Get 2FA status for user"""
        tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
        
        if not tfa:
            return {
                "is_enabled": False,
                "is_configured": False
            }
        
        return {
            "is_enabled": tfa.is_enabled,
            "is_configured": True,
            "enabled_at": tfa.verified_at.isoformat() if tfa.verified_at else None
        }

    def regenerate_backup_codes(self, user_id: int, code: str) -> Dict[str, Any]:
        """Regenerate backup codes (requires valid 2FA code)"""
        try:
            tfa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
            if not tfa or not tfa.is_enabled:
                return {"error": "2FA is not enabled"}

            # Verify current code
            totp = pyotp.TOTP(tfa.secret)
            if not totp.verify(code, valid_window=1):
                return {"error": "Invalid verification code"}

            # Generate new backup codes
            backup_codes = self._generate_backup_codes()
            tfa.backup_codes = self._hash_backup_codes(backup_codes)
            db.session.commit()

            return {
                "success": True,
                "backup_codes": backup_codes,
                "message": "New backup codes generated. Previous codes are now invalid."
            }

        except Exception as e:
            logger.error(f"Failed to regenerate backup codes: {e}")
            return {"error": str(e)}

    def _generate_qr_code(self, data: str) -> str:
        """Generate QR code as base64 image"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    def _generate_backup_codes(self, count: int = 10) -> list:
        """Generate backup codes"""
        import secrets
        return [secrets.token_hex(4).upper() for _ in range(count)]

    def _hash_backup_codes(self, codes: list) -> list:
        """Hash backup codes for storage"""
        import hashlib
        return [hashlib.sha256(code.encode()).hexdigest() for code in codes]

    def _verify_backup_code(self, tfa: TwoFactorAuth, code: str) -> bool:
        """Verify and consume a backup code"""
        if not tfa.backup_codes:
            return False
        
        import hashlib
        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()
        
        if code_hash in tfa.backup_codes:
            # Remove used code
            tfa.backup_codes.remove(code_hash)
            db.session.commit()
            return True
        
        return False
