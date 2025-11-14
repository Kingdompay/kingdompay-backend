# KingdomPay Quick Start Guide

Get KingdomPay running locally in 5 minutes.

## Prerequisites

- Docker and Docker Compose
- Git
- (Optional) Postman or curl for API testing

## Step 1: Clone and Setup

```bash
cd kingdompay-backend
cp env.example .env
```

Edit `.env` and set:
- `SECRET_KEY` (generate a random string)
- `JWT_SECRET_KEY` (generate a random string)
- `ENCRYPTION_KEY` (32-byte key, e.g., `openssl rand -hex 32`)

## Step 2: Start Services

```bash
# Start database, Redis, and backend
docker-compose up -d

# Wait for services to be ready (about 30 seconds)
docker-compose ps
```

## Step 3: Initialize Database

```bash
# Run migrations
docker-compose exec backend flask db upgrade

# Initialize system wallets
docker-compose exec backend python3 scripts/init_system.py
```

## Step 4: Verify Installation

```bash
# Check health endpoint
curl http://localhost:5001/health

# Should return: {"status": "healthy"}
```

## Step 5: Create Your First User

```bash
# Request OTP
curl -X POST http://localhost:5001/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254712345678"}'

# Verify OTP (use code from SMS/logs)
curl -X POST http://localhost:5001/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254712345678", "otp": "123456"}'

# Save the access_token from the response
```

## Step 6: Test a Transfer

```bash
# Get your wallet ID from the user response, then:
curl -X POST http://localhost:5001/api/v1/transfers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-transfer-$(date +%s)" \
  -d '{
    "to_wallet": "WAL-PLATFORM-001",
    "amount": 100,
    "memo": "Test transfer"
  }'
```

## Step 7: Create a Community

```bash
curl -X POST http://localhost:5001/api/v1/communities \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Church",
    "type": "CHURCH",
    "slug": "test-church"
  }'
```

## Next Steps

- **Provider Integration**: Set up M-Pesa/Airtel/T-Kash credentials in `.env` (see `docs/STAGING_BRINGUP.md`)
- **Webhooks**: Configure provider callbacks (see `docs/WEBHOOK_INTEGRATION.md`)
- **SDK**: Integrate JS SDK into your frontend (see `sdk/js/README.md`)
- **Testing**: Run test suite: `docker-compose exec backend pytest`

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend flask db upgrade

# Create migration
docker-compose exec backend flask db migrate -m "Description"

# Run tests
docker-compose exec backend pytest

# Access database
docker-compose exec postgres psql -U admin -d kingdompay

# Stop services
docker-compose down

# Restart services
docker-compose restart backend
```

## Troubleshooting

### Port Already in Use

If port 5001 is taken, edit `docker-compose.yml`:
```yaml
ports:
  - "5002:5000"  # Change 5001 to 5002
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Migration Errors

```bash
# Check current migration status
docker-compose exec backend flask db current

# Rollback last migration
docker-compose exec backend flask db downgrade -1

# Re-run migrations
docker-compose exec backend flask db upgrade
```

### System Wallets Not Created

```bash
# Manually initialize
docker-compose exec backend python3 scripts/init_system.py
```

## Production Deployment

For production deployment, see:
- `docs/STAGING_BRINGUP.md` - Staging environment setup
- `docker-compose.production.yml` - Production configuration
- `scripts/deploy.sh` - Automated deployment script

## Support

- Documentation: `/docs`
- API Reference: `/docs/api.md` (when available)
- Issues: GitHub Issues

