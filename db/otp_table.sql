-- OTP verification table for KingdomPay
CREATE TABLE otp_verifications (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- Create index for phone number lookups
CREATE INDEX idx_otp_phone_number ON otp_verifications(phone_number);
-- Create index for cleanup of expired OTPs
CREATE INDEX idx_otp_expires_at ON otp_verifications(expires_at);