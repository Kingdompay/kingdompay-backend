# Ledger (Double-Entry)

- Tables: ledger_journals, ledger_entries
- Rule: debits == credits per journal
- Account: WALLET_CASH for wallet movements
- Idempotency: unique per request to avoid duplicate postings
