"""
Validation and error handling utilities for KingdomPay
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from flask import request, jsonify
from marshmallow import Schema, fields, validate, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from werkzeug.exceptions import (
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    InternalServerError,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from extensions import db

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""

    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class BusinessLogicError(Exception):
    """Custom business logic error"""

    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


# Input validation schemas
class PhoneNumberField(fields.Field):
    """Custom field for phone number validation"""

    def _serialize(self, value, attr, obj, **kwargs):
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        if not value:
            raise ValidationError("Phone number is required")

        # Clean phone number
        cleaned = re.sub(r"\D", "", str(value))

        # Validate Kenyan phone number format
        if cleaned.startswith("254") and len(cleaned) == 12:
            return f"+{cleaned}"
        elif cleaned.startswith("0") and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"
        elif len(cleaned) == 9:
            return f"+254{cleaned}"
        else:
            raise ValidationError("Invalid phone number format")


class AmountField(fields.Decimal):
    """Custom field for monetary amounts"""

    def __init__(
        self, min_amount: float = 0.01, max_amount: float = 1000000.0, **kwargs
    ):
        super().__init__(places=2, **kwargs)
        self.min_amount = min_amount
        self.max_amount = max_amount

    def _deserialize(self, value, attr, data, **kwargs):
        amount = super()._deserialize(value, attr, data, **kwargs)

        if amount < self.min_amount:
            raise ValidationError(f"Amount must be at least {self.min_amount}")

        if amount > self.max_amount:
            raise ValidationError(f"Amount cannot exceed {self.max_amount}")

        return amount


# Common validation schemas
class PaginationSchema(Schema):
    """Pagination parameters"""

    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))


class UserRegistrationSchema(Schema):
    """User registration validation"""

    phone_number = PhoneNumberField(required=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(allow_none=True)


class OTPVerificationSchema(Schema):
    """OTP verification validation"""

    phone_number = PhoneNumberField(required=True)
    otp_code = fields.Str(required=True, validate=validate.Length(min=4, max=8))


class TransactionSchema(Schema):
    """Transaction validation"""

    amount = AmountField(required=True)
    description = fields.Str(validate=validate.Length(max=500))
    reference = fields.Str(validate=validate.Length(max=100))


class WalletTransferSchema(Schema):
    """Wallet transfer validation"""

    destination_wallet_id = fields.Int(required=True, validate=validate.Range(min=1))
    amount = AmountField(required=True)
    description = fields.Str(validate=validate.Length(max=500))
    reference = fields.Str(validate=validate.Length(max=100))


class CommunityCreationSchema(Schema):
    """Community creation validation"""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    description = fields.Str(validate=validate.Length(max=500))
    community_type = fields.Str(
        validate=validate.OneOf(["church", "ministry", "group", "other"])
    )


# Error response utilities
def create_error_response(
    message: str,
    code: str = None,
    field: str = None,
    details: Dict = None,
    status_code: int = 400,
) -> tuple:
    """Create standardized error response"""
    error_data = {
        "error": True,
        "message": message,
        "code": code,
        "field": field,
        "details": details or {},
    }

    # Remove None values
    error_data = {k: v for k, v in error_data.items() if v is not None}

    return jsonify(error_data), status_code


def handle_validation_error(error: ValidationError) -> tuple:
    """Handle marshmallow validation errors"""
    if isinstance(error.messages, dict):
        # Multiple field errors
        first_error = next(iter(error.messages.values()))[0]
        field = next(iter(error.messages.keys()))
        return create_error_response(
            message=first_error, field=field, code="VALIDATION_ERROR", status_code=400
        )
    else:
        # Single error
        return create_error_response(
            message=str(error), code="VALIDATION_ERROR", status_code=400
        )


def handle_database_error(error: SQLAlchemyError) -> tuple:
    """Handle database errors"""
    db.session.rollback()

    if isinstance(error, IntegrityError):
        # Check for specific constraint violations
        error_msg = str(error.orig)

        if "UNIQUE constraint failed" in error_msg or "duplicate key" in error_msg:
            if "phone_number" in error_msg:
                return create_error_response(
                    message="Phone number already registered",
                    code="DUPLICATE_PHONE",
                    status_code=409,
                )
            elif "email" in error_msg:
                return create_error_response(
                    message="Email already registered",
                    code="DUPLICATE_EMAIL",
                    status_code=409,
                )
            else:
                return create_error_response(
                    message="Duplicate entry", code="DUPLICATE_ENTRY", status_code=409
                )
        elif "FOREIGN KEY constraint failed" in error_msg:
            return create_error_response(
                message="Referenced resource not found",
                code="INVALID_REFERENCE",
                status_code=400,
            )
        else:
            return create_error_response(
                message="Database constraint violation",
                code="CONSTRAINT_ERROR",
                status_code=400,
            )
    else:
        logger.error(f"Database error: {str(error)}")
        return create_error_response(
            message="Database operation failed", code="DATABASE_ERROR", status_code=500
        )


def handle_business_logic_error(error: BusinessLogicError) -> tuple:
    """Handle business logic errors"""
    return create_error_response(
        message=error.message, code=error.code, details=error.details, status_code=400
    )


# Request validation decorator
def validate_request(schema_class):
    """Decorator to validate request data"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                schema = schema_class()

                # Get JSON data
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()

                # Validate data
                validated_data = schema.load(data)

                # Add validated data to kwargs
                kwargs["validated_data"] = validated_data

                return func(*args, **kwargs)

            except ValidationError as e:
                return handle_validation_error(e)
            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
                return create_error_response(
                    message="Invalid request data",
                    code="INVALID_REQUEST",
                    status_code=400,
                )

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


# Common validation functions
def validate_phone_number(phone_number: str) -> Optional[str]:
    """Validate and normalize phone number"""
    if not phone_number:
        return None

    cleaned = re.sub(r"\D", "", str(phone_number))

    if cleaned.startswith("254") and len(cleaned) == 12:
        return f"+{cleaned}"
    elif cleaned.startswith("0") and len(cleaned) == 10:
        return f"+254{cleaned[1:]}"
    elif len(cleaned) == 9:
        return f"+254{cleaned}"
    else:
        return None


def validate_amount(
    amount: Union[int, float, str],
    min_amount: float = 0.01,
    max_amount: float = 1000000.0,
) -> float:
    """Validate monetary amount"""
    try:
        amount_float = float(amount)

        if amount_float < min_amount:
            raise ValidationError(f"Amount must be at least {min_amount}")

        if amount_float > max_amount:
            raise ValidationError(f"Amount cannot exceed {max_amount}")

        return round(amount_float, 2)

    except (ValueError, TypeError):
        raise ValidationError("Invalid amount format")


def validate_email(email: str) -> Optional[str]:
    """Validate email format"""
    if not email:
        return None

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(email_pattern, email):
        return email.lower()
    else:
        raise ValidationError("Invalid email format")


def validate_password_strength(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one number")

    return True


# Rate limiting helpers
def get_rate_limit_key():
    """Get rate limiting key based on user or IP"""
    from flask_jwt_extended import get_jwt_identity

    user_id = get_jwt_identity()
    if user_id:
        return f"user:{user_id}"
    else:
        return f"ip:{request.remote_addr}"


# Security helpers
def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', "", str(text))

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def validate_file_upload(
    file, allowed_extensions: List[str] = None, max_size: int = 5 * 1024 * 1024
) -> bool:
    """Validate file upload"""
    if not file:
        raise ValidationError("No file provided")

    if file.content_length > max_size:
        raise ValidationError(f"File size exceeds {max_size // (1024*1024)}MB limit")

    if allowed_extensions:
        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
                f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )

    return True
