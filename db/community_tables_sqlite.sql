-- Community Tables for KingdomPay (SQLite Version)
-- Run this after the main tables are created
-- Community Roles table (reference table)
CREATE TABLE IF NOT EXISTS community_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id TEXT UNIQUE NOT NULL DEFAULT (
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6)))
    ),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT
);
-- Communities table
CREATE TABLE IF NOT EXISTS communities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    community_id TEXT UNIQUE NOT NULL DEFAULT (
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6)))
    ),
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Community Members junction table
CREATE TABLE IF NOT EXISTS community_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES community_roles(id) ON DELETE
    SET NULL,
        role TEXT,
        joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        UNIQUE(user_id, community_id)
);
-- Contributions table
CREATE TABLE IF NOT EXISTS contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    amount DECIMAL(15, 2) NOT NULL,
    contribution_type TEXT NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Add contribution_id to existing transactions table (if it doesn't exist)
-- Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we'll handle this in the migration script
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
-- Insert default community roles (using INSERT OR IGNORE for SQLite)
INSERT
    OR IGNORE INTO community_roles (role_name, description)
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
    );
-- Note: Trigger for auto-updating updated_at timestamp is not included in SQLite version
-- You can implement this functionality in your application code if needed