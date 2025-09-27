-- KYC Tables for KingdomPay
-- Run this after the main tables are created
-- KYC Documents table
CREATE TABLE IF NOT EXISTS kyc_documents (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL CHECK (
        document_type IN (
            'national_id',
            'passport',
            'drivers_license',
            'utility_bill',
            'bank_statement',
            'employment_letter'
        )
    ),
    file_path VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'approved',
            'rejected',
            'expired',
            'under_review'
        )
    ),
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    rejection_reason TEXT,
    extracted_data JSONB,
    confidence_score FLOAT,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    CONSTRAINT kyc_documents_file_size_positive CHECK (file_size > 0),
    CONSTRAINT kyc_documents_confidence_score_range CHECK (
        confidence_score IS NULL
        OR (
            confidence_score >= 0
            AND confidence_score <= 1
        )
    )
);
-- KYC Verifications table
CREATE TABLE IF NOT EXISTS kyc_verifications (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL DEFAULT 'tier_0' CHECK (tier IN ('tier_0', 'tier_1', 'tier_2')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'approved',
            'rejected',
            'expired',
            'under_review'
        )
    ),
    encrypted_personal_data TEXT,
    daily_limit DECIMAL(15, 2) NOT NULL DEFAULT 0,
    monthly_limit DECIMAL(15, 2) NOT NULL DEFAULT 0,
    yearly_limit DECIMAL(15, 2) NOT NULL DEFAULT 0,
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    rejection_reason TEXT,
    pep_check BOOLEAN NOT NULL DEFAULT FALSE,
    sanctions_check BOOLEAN NOT NULL DEFAULT FALSE,
    aml_check BOOLEAN NOT NULL DEFAULT FALSE,
    risk_score FLOAT CHECK (
        risk_score IS NULL
        OR (
            risk_score >= 0
            AND risk_score <= 100
        )
    ),
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    CONSTRAINT kyc_verifications_limits_positive CHECK (
        daily_limit >= 0
        AND monthly_limit >= 0
        AND yearly_limit >= 0
    )
);
-- KYC Audit Logs table
CREATE TABLE IF NOT EXISTS kyc_audit_logs (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kyc_verification_id INTEGER REFERENCES kyc_verifications(id) ON DELETE CASCADE,
    kyc_document_id INTEGER REFERENCES kyc_documents(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    old_tier VARCHAR(50),
    new_tier VARCHAR(50),
    performed_by INTEGER REFERENCES users(id),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    metadata JSONB,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_kyc_documents_user_id ON kyc_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_documents_status ON kyc_documents(status);
CREATE INDEX IF NOT EXISTS idx_kyc_documents_type ON kyc_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_kyc_documents_hash ON kyc_documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_user_id ON kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_status ON kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_tier ON kyc_verifications(tier);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_risk_score ON kyc_verifications(risk_score);
CREATE INDEX IF NOT EXISTS idx_kyc_audit_logs_user_id ON kyc_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_audit_logs_action ON kyc_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_kyc_audit_logs_created_at ON kyc_audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_kyc_audit_logs_performed_by ON kyc_audit_logs(performed_by);
-- Add triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER update_kyc_verifications_updated_at BEFORE
UPDATE ON kyc_verifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Add comments for documentation
COMMENT ON TABLE kyc_documents IS 'Stores uploaded KYC documents with verification status';
COMMENT ON TABLE kyc_verifications IS 'Tracks user KYC verification status and limits';
COMMENT ON TABLE kyc_audit_logs IS 'Audit trail for all KYC-related actions';
COMMENT ON COLUMN kyc_documents.file_hash IS 'SHA-256 hash for duplicate detection';
COMMENT ON COLUMN kyc_documents.extracted_data IS 'OCR extracted information from document';
COMMENT ON COLUMN kyc_documents.confidence_score IS 'OCR confidence score (0-1)';
COMMENT ON COLUMN kyc_verifications.encrypted_personal_data IS 'Encrypted personal information';
COMMENT ON COLUMN kyc_verifications.pep_check IS 'Politically Exposed Person check';
COMMENT ON COLUMN kyc_verifications.sanctions_check IS 'Sanctions list check';
COMMENT ON COLUMN kyc_verifications.aml_check IS 'Anti-Money Laundering check';
COMMENT ON COLUMN kyc_verifications.risk_score IS 'Calculated risk score (0-100)';
COMMENT ON COLUMN kyc_verifications.risk_level IS 'Risk level classification';