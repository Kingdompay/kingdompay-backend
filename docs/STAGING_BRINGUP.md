# Staging Bring-Up Guide

## 1) Environment variables

Copy `env.staging.example` to your staging secret store (Vault/SSM). Required keys:

- Core
  - `APP_ENV=staging`
  - `SECRET_KEY=`
  - `JWT_SECRET_KEY=`
  - `SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host:5432/kingdompay`
  - `RATELIMIT_STORAGE_URL=redis://host:6379/0`
  - `REDIS_URL=redis://host:6379/0`
  - `BASE_URL=https://staging.api.kingdompay.example`

- Webhooks
  - `WEBHOOK_SECRET=` (for signing outbound webhooks)
  - `MPESA_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/MPESA`
  - `AIRTEL_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/AIRTEL`
  - `TKASH_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/TKASH`

- M-Pesa (Daraja)
  - `MPESA_CONSUMER_KEY=`
  - `MPESA_CONSUMER_SECRET=`
  - `MPESA_PASSKEY=`
  - `MPESA_SHORTCODE=`
  - `MPESA_INITIATOR_NAME=`
  - `MPESA_SECURITY_CREDENTIAL=`
  - `MPESA_BASE_URL=https://sandbox.safaricom.co.ke`
  - `MPESA_B2C_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/MPESA`

- Airtel Money
  - `AIRTEL_CLIENT_ID=`
  - `AIRTEL_CLIENT_SECRET=`
  - `AIRTEL_BASE_URL=https://openapiuat.airtel.africa`
  - `AIRTEL_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/AIRTEL`

- T-Kash
  - `TKASH_API_KEY=`
  - `TKASH_API_SECRET=`
  - `TKASH_MERCHANT_ID=`
  - `TKASH_BASE_URL=https://api.t-kash.co.ke`
  - `TKASH_CALLBACK_URL=$BASE_URL/api/v1/webhooks/provider/TKASH`

## 2) Database migration

```bash
# From repo root
export FLASK_APP=app.py
flask db upgrade
```

If upgrading an existing DB that lacks wallet fields, ensure:
- `wallets.owner_type` (VARCHAR, default 'USER')
- `wallets.owner_id` (INT, default 0)
- `wallets.user_id` is nullable

## 3) First boot

On first boot the app will:
- Initialize platform and federal wallets
- Create system webhook signer

Verify wallets:
```sql
select id, owner_type, owner_id, display_number, balance from wallets where owner_type in ('PLATFORM','FEDERAL');
```

## 4) Provider checks

- M-Pesa OAuth: check logs for access token success
- STK Push flow:
  1. `POST /api/v1/topups/momo` with `provider=MPESA`
  2. Confirm STK prompt on device
  3. Verify webhook received and wallet balance updates

## 5) Transfers & payouts

- Transfers: `POST /api/v1/transfers` with Idempotency-Key header
- Community payouts:
  1. `POST /api/v1/payouts` (COMMUNITY wallet) → returns `approval_id`
  2. Admins sign: `POST /api/v1/approvals/{id}/sign`
  3. Execute: `POST /api/v1/payouts/{approval_id}/execute`

## 6) Reconciliation

- Manual run: `POST /api/v1/reconciliation/reconcile` (admin)
- Reports: `GET /api/v1/reconciliation/reports`

## 7) Risk & limits

- Adjust velocity thresholds in `RiskService`
- Blacklist sample entries and verify blocking

## 8) Observability

- Expose logs and metrics; add Grafana panels per `docs/observability/dashboards.md`

## 9) Rollback plan

- Keep DB snapshot before upgrade
- Feature flag new providers
- Canary % traffic on checkout before full cutover


