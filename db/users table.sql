CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users
ALTER COLUMN created_at TYPE TIMESTAMPTZ
USING created_at AT TIME ZONE 'UTC';

ALTER TABLE users
ADD CONSTRAINT unique_email UNIQUE (email);

CREATE INDEX idx_users_email ON users(email);

ALTER TABLE users
ADD COLUMN phone_number VARCHAR(20) UNIQUE,
ADD COLUMN is_phone_verified BOOLEAN DEFAULT FALSE;

ALTER TABLE users
ADD COLUMN last_login TIMESTAMPTZ;

ALTER TABLE users
ALTER COLUMN phone_number SET NOT NULL;


ALTER TABLE users
ADD COLUMN updated_at TIMESTAMPTZ,
ADD COLUMN reset_token VARCHAR(255),
ADD COLUMN reset_token_expires TIMESTAMPTZ,
ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

CREATE INDEX idx_users_reset_token ON users(reset_token);


SELECT * FROM users;

