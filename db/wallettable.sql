CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE wallets (
    id SERIAL PRIMARY KEY,  
    user_id INT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    
    wallet_number UUID UNIQUE DEFAULT gen_random_uuid(),  

    balance NUMERIC(15,2) DEFAULT 0.00 NOT NULL CHECK (balance >= 0), 

    currency VARCHAR(3) NOT NULL DEFAULT 'KES' CHECK (currency IN ('KES','USD','EUR')),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wallets_user_id ON wallets(user_id);


CREATE OR REPLACE FUNCTION create_wallet_for_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO wallets (user_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_user_insert
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_wallet_for_user();


CREATE OR REPLACE FUNCTION update_wallet_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_wallet_updated_at
BEFORE UPDATE ON wallets
FOR EACH ROW
EXECUTE FUNCTION update_wallet_timestamp();


ALTER TABLE wallets
ADD COLUMN display_number VARCHAR(20) UNIQUE DEFAULT concat('WAL-', floor(random() * 1000000000)::bigint);


