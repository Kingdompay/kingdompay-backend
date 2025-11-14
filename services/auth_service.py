"""
Authentication service for KingdomPay
Handles OTP verification, JWT tokens, and user management
"""

import re
from datetime import datetime, timezone, timedelta
from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash
from extensions import db
from models.user import User
from models.otp import OTPVerification
from services.sms_service import SMSService
from services.encryption_service import EncryptionService


class AuthService:
    """Authentication service for user management and OTP verification"""

    def __init__(self):
        self.sms_service = SMSService()
        self.encryption_service = EncryptionService()

    def validate_phone_number(self, phone_number):
        """Validate phone number format"""
        # Remove any non-digit characters
        cleaned = re.sub(r"\D", "", phone_number)

        # Check if it's a valid Kenyan phone number
        if cleaned.startswith("254"):
            return f"+{cleaned}"
        elif cleaned.startswith("0") and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"
        elif len(cleaned) == 9:
            return f"+254{cleaned}"
        else:
            return None

    def send_otp(self, phone_number):
        """Send OTP to phone number"""
        # Validate phone number
        validated_phone = self.validate_phone_number(phone_number)
        if not validated_phone:
            return {"success": False, "message": "Invalid phone number format"}

        # Check rate limiting
        recent_attempts = OTPVerification.get_recent_attempts(
            validated_phone, minutes=5
        )
        # Align with route-level limiter (5 per minute): allow first 5 attempts
        if recent_attempts >= 5:
            return {
                "success": False,
                "message": "Too many OTP requests. Please wait 5 minutes.",
            }

        # Generate OTP
        otp = OTPVerification.generate_otp(validated_phone)

        # Send SMS
        message = f"Your KingdomPay verification code is: {otp.otp_code}. Valid for 5 minutes."
        sms_result = self.sms_service.send_sms(validated_phone, message)

        # In development, include OTP in response for testing
        response = {
            "success": True,
            "message": "OTP sent successfully",
            "phone_number": validated_phone,
        }
        
        # Include OTP if: development mode OR no SMS provider configured (for testing)
        is_development = (
            current_app.config.get("FLASK_ENV") == "development"
            or current_app.config.get("APP_ENV") == "development"
            or not self.sms_service.api_key  # No SMS provider configured
        )
        
        if is_development:
            current_app.logger.info(f"OTP for {validated_phone}: {otp.otp_code}")
            response["otp_code"] = otp.otp_code  # Include OTP for testing
            response["message"] = (
                "OTP sent successfully (development mode - OTP included in response)"
            )

        if sms_result["success"]:
            return response
        else:
            return {
                "success": False,
                "message": "Failed to send OTP. Please try again.",
            }

    def verify_otp(self, phone_number, otp_code, full_name=None):
        """Verify OTP and create/update user with proper race condition handling"""
        # Validate phone number
        validated_phone = self.validate_phone_number(phone_number)
        if not validated_phone:
            return {"success": False, "message": "Invalid phone number format"}

        # Verify OTP
        if not OTPVerification.verify_otp(validated_phone, otp_code):
            return {"success": False, "message": "Invalid or expired OTP"}

        # Use database transaction with proper error handling for race conditions
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Note: We don't need to explicitly begin a transaction
                # Flask-SQLAlchemy manages this automatically

                # Find or create user with proper locking
                user = User.find_by_phone(validated_phone)
                if not user:
                    if not full_name:
                        db.session.rollback()
                        return {
                            "success": False,
                            "message": "Full name is required for new users",
                        }

                    # Create new user with proper error handling
                    try:
                        user = User(
                            full_name=full_name,
                            phone_number=validated_phone,
                            is_phone_verified=True,
                        )
                        db.session.add(user)
                        db.session.flush()  # Get user ID without committing

                        # Create wallet for new user
                        from models.wallet import Wallet

                        # Create wallet for new user
                        # Wallet.__init__ will automatically set owner_type and owner_id from user_id
                        wallet = Wallet(
                            user_id=user.id,
                            currency="KES",
                        )
                        db.session.add(wallet)
                        db.session.commit()

                        current_app.logger.info(
                            f"Successfully created user {user.id} and wallet {wallet.id} for {validated_phone}"
                        )

                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.exception(
                            f"Error creating user account (attempt {attempt + 1}): {str(e)}"
                        )

                        # Check if it's a unique constraint violation
                        if (
                            "UNIQUE constraint failed" in str(e)
                            or "duplicate key" in str(e).lower()
                            or "unique constraint" in str(e).lower()
                        ):
                            # User was created by another concurrent request
                            current_app.logger.info(
                                f"Unique constraint violation detected, retrying..."
                            )
                            if attempt < max_retries - 1:
                                continue  # Retry
                            else:
                                # Final attempt - try to find the user that was created
                                user = User.find_by_phone(validated_phone)
                                if user:
                                    # Update existing user
                                    user.is_phone_verified = True
                                    if full_name:
                                        user.full_name = full_name
                                    db.session.commit()
                                    break
                                else:
                                    current_app.logger.error(
                                        f"User not found after unique constraint violation: {validated_phone}"
                                    )
                                    return {
                                        "success": False,
                                        "message": f"Failed to create user account: {str(e)}",
                                    }
                        else:
                            # Log the actual error for debugging
                            error_message = str(e)
                            current_app.logger.error(
                                f"Failed to create user: {error_message}"
                            )
                            return {
                                "success": False,
                                "message": f"Failed to create user account: {error_message}",
                            }
                else:
                    # Update existing user
                    user.is_phone_verified = True
                    if full_name:
                        user.full_name = full_name
                    db.session.commit()

                # Generate tokens
                # Use string identity for JWT to avoid type-related issues in some configurations
                access_token = create_access_token(identity=str(user.id))
                refresh_token = create_refresh_token(identity=str(user.id))

                # Update last login
                user.update_last_login()

                return {
                    "success": True,
                    "message": "OTP verified successfully",
                    "user": user.to_dict(),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }

            except Exception as e:
                db.session.rollback()
                current_app.logger.exception(
                    f"Error in verify_otp (attempt {attempt + 1}): {str(e)}"
                )
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    return {
                        "success": False,
                        "message": f"Failed to process verification: {str(e)}",
                    }

        return {
            "success": False,
            "message": "Failed to process verification after multiple attempts",
        }

    def refresh_token(self):
        """Refresh access token using the current refresh token context"""
        try:
            # Identity may be stored as string; cast to int for DB lookup
            user_id = get_jwt_identity()
            try:
                user_id_int = int(user_id)
            except (TypeError, ValueError):
                return {"success": False, "message": "Invalid refresh token"}

            user = User.query.get(user_id_int)

            if not user or not user.is_active:
                return {"success": False, "message": "Invalid refresh token"}

            # Ensure identity is a string for consistency
            new_access_token = create_access_token(identity=str(user_id))

            return {"success": True, "access_token": new_access_token}
        except Exception:
            return {"success": False, "message": "Invalid refresh token"}

    def get_current_user(self):
        """Get current user from JWT token"""
        try:
            user_id = get_jwt_identity()
            try:
                user_id_int = int(user_id)
            except (TypeError, ValueError):
                return None

            user = User.query.get(user_id_int)

            if not user or not user.is_active:
                return None

            return user
        except Exception:
            return None

    def logout(self, user_id):
        """Logout user (in a real app, you'd blacklist the token)"""
        # For now, we'll just update last login
        user = User.query.get(user_id)
        if user:
            user.update_last_login()
            db.session.commit()

        return {"success": True, "message": "Logged out successfully"}

    def update_profile(self, user_id, data):
        """Update user profile with proper race condition handling"""
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "Invalid user"}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user = User.query.get(user_id)
                if not user:
                    db.session.rollback()
                    return {"success": False, "message": "User not found"}

                # Update allowed fields
                if "full_name" in data:
                    user.full_name = data["full_name"]

                if "email" in data:
                    # Check if email is already taken
                    existing_user = User.find_by_email(data["email"])
                    if existing_user and existing_user.id != user_id:
                        db.session.rollback()
                        return {"success": False, "message": "Email already taken"}
                    user.email = data["email"]

                user.updated_at = datetime.now(timezone.utc)
                db.session.commit()

                return {
                    "success": True,
                    "message": "Profile updated successfully",
                    "user": user.to_dict(),
                }

            except Exception as e:
                db.session.rollback()
                if (
                    "UNIQUE constraint failed" in str(e)
                    or "duplicate key" in str(e).lower()
                ):
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        return {"success": False, "message": "Email already taken"}
                else:
                    return {"success": False, "message": "Failed to update profile"}

        return {
            "success": False,
            "message": "Failed to update profile after multiple attempts",
        }

    def cleanup_expired_otps(self):
        """Clean up expired OTPs (call this periodically)"""
        cleaned = OTPVerification.cleanup_expired()
        return {"success": True, "cleaned_count": cleaned}
