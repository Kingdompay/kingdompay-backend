CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,

    -- Who sent the money (NULL for deposits)
    source_wallet_id INT REFERENCES wallets(id) ON DELETE CASCADE,

    -- Who received the money (NULL for withdrawals)
    destination_wallet_id INT REFERENCES wallets(id) ON DELETE CASCADE,

   
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN (
        'DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT'
    )),

    -- Amount moved
    amount NUMERIC(15,2) NOT NULL CHECK (amount > 0),

    source_balance_after NUMERIC(15,2),

    destination_balance_after NUMERIC(15,2),

    reference_number VARCHAR(30) UNIQUE DEFAULT concat('TX-', floor(random() * 1000000000000)::bigint),

    -- Transaction status
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'
        CHECK (status IN ('PENDING','SUCCESS','FAILED')),

 
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_transactions_source_wallet ON transactions(source_wallet_id);
CREATE INDEX idx_transactions_destination_wallet ON transactions(destination_wallet_id);
CREATE INDEX idx_transactions_reference ON transactions(reference_number);



CREATE OR REPLACE FUNCTION add_transaction(
    p_source_wallet_id INT,
    p_destination_wallet_id INT,
    p_type VARCHAR,
    p_amount NUMERIC,
    p_description TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    new_source_balance NUMERIC(15,2);
    new_destination_balance NUMERIC(15,2);
BEGIN
    
    PERFORM pg_advisory_xact_lock(1);  

    -- Deposit
    IF p_type = 'DEPOSIT' THEN
        UPDATE wallets
        SET balance = balance + p_amount, updated_at = now()
        WHERE id = p_destination_wallet_id
        RETURNING balance INTO new_destination_balance;

        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, destination_balance_after, description, status
        )
        VALUES (NULL, p_destination_wallet_id, 'DEPOSIT',
            p_amount, new_destination_balance, p_description, 'SUCCESS');

    -- Withdrawal
    ELSIF p_type = 'WITHDRAWAL' THEN
        UPDATE wallets
        SET balance = balance - p_amount, updated_at = now()
        WHERE id = p_source_wallet_id AND balance >= p_amount
        RETURNING balance INTO new_source_balance;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Insufficient funds in wallet %', p_source_wallet_id;
        END IF;

        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, source_balance_after, description, status
        )
        VALUES (p_source_wallet_id, NULL, 'WITHDRAWAL',
            p_amount, new_source_balance, p_description, 'SUCCESS');

    -- Transfer / Payment
    ELSIF p_type IN ('TRANSFER', 'PAYMENT') THEN
        -- Debit sender
        UPDATE wallets
        SET balance = balance - p_amount, updated_at = now()
        WHERE id = p_source_wallet_id AND balance >= p_amount
        RETURNING balance INTO new_source_balance;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Insufficient funds in wallet %', p_source_wallet_id;
        END IF;

        -- Credit receiver
        UPDATE wallets
        SET balance = balance + p_amount, updated_at = now()
        WHERE id = p_destination_wallet_id
        RETURNING balance INTO new_destination_balance;

        -- Log transaction
        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, source_balance_after, destination_balance_after, description, status
        )
        VALUES (p_source_wallet_id, p_destination_wallet_id, p_type,
            p_amount, new_source_balance, new_destination_balance, p_description, 'SUCCESS');

    ELSE
        RAISE EXCEPTION 'Invalid transaction type: %', p_type;
    END IF;
END;
$$ LANGUAGE plpgsql;



