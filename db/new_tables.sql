-- New tables for KingdomPay features
-- Run this file to create notifications, scheduled_payments, and two_factor_auth tables

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type VARCHAR(50),
    title VARCHAR(200),
    message TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read);

-- Scheduled payments table
CREATE TABLE IF NOT EXISTS scheduled_payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    recipient_wallet_id INTEGER REFERENCES wallets(id),
    recipient_phone VARCHAR(20),
    amount NUMERIC(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'KES',
    description VARCHAR(255),
    frequency VARCHAR(20) NOT NULL,
    next_run TIMESTAMPTZ NOT NULL,
    last_run TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    run_count INTEGER DEFAULT 0,
    max_runs INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_user ON scheduled_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_next ON scheduled_payments(next_run);

-- Two-factor authentication table
CREATE TABLE IF NOT EXISTS two_factor_auth (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    secret VARCHAR(32) NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE,
    backup_codes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

-- Done!
SELECT 'Tables created successfully!' as status;
