-- Community Tables for KingdomPay
-- Run this after the main tables are created
-- Community Roles table (reference table)
CREATE TABLE IF NOT EXISTS community_roles (
    id SERIAL PRIMARY KEY,
    role_id VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);
-- Communities table
CREATE TABLE IF NOT EXISTS communities (
    id SERIAL PRIMARY KEY,
    community_id VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Community Members junction table
CREATE TABLE IF NOT EXISTS community_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES community_roles(id) ON DELETE
    SET NULL,
        role VARCHAR(50),
        joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        UNIQUE(user_id, community_id)
);
-- Contributions table
CREATE TABLE IF NOT EXISTS contributions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    amount DECIMAL(15, 2) NOT NULL,
    contribution_type VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Add contribution_id to existing transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS contribution_id INTEGER REFERENCES contributions(id) ON DELETE
SET NULL;
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_communities_created_by ON communities(created_by);
CREATE INDEX IF NOT EXISTS idx_communities_type ON communities(type);
CREATE INDEX IF NOT EXISTS idx_communities_created_at ON communities(created_at);
CREATE INDEX IF NOT EXISTS idx_community_members_user_id ON community_members(user_id);
CREATE INDEX IF NOT EXISTS idx_community_members_community_id ON community_members(community_id);
CREATE INDEX IF NOT EXISTS idx_community_members_role_id ON community_members(role_id);
CREATE INDEX IF NOT EXISTS idx_contributions_user_id ON contributions(user_id);
CREATE INDEX IF NOT EXISTS idx_contributions_community_id ON contributions(community_id);
CREATE INDEX IF NOT EXISTS idx_contributions_created_at ON contributions(created_at);
CREATE INDEX IF NOT EXISTS idx_contributions_type ON contributions(contribution_type);
CREATE INDEX IF NOT EXISTS idx_transactions_contribution_id ON transactions(contribution_id);
-- Insert default community roles
INSERT INTO community_roles (role_name, description)
VALUES (
        'admin',
        'Community administrator with full management rights'
    ),
    (
        'moderator',
        'Community moderator with limited management rights'
    ),
    ('member', 'Regular community member'),
    (
        'treasurer',
        'Community treasurer responsible for financial management'
    ),
    (
        'secretary',
        'Community secretary responsible for record keeping'
    ) ON CONFLICT (role_name) DO NOTHING;
-- Create trigger to update updated_at timestamp for communities
CREATE OR REPLACE FUNCTION update_communities_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trigger_update_communities_updated_at BEFORE
UPDATE ON communities FOR EACH ROW EXECUTE FUNCTION update_communities_updated_at();