# Quick Phase 2 Testing Guide

## 🚀 Quick Start Testing

### 1. Run Database Migration
```bash
cd kingdompay-backend
flask db migrate -m "Phase 2: fees, multisig, risk models"
flask db upgrade
```

### 2. Start Server
```bash
python run.py
```

### 3. Get Auth Token
```bash
# Request OTP
curl -X POST http://localhost:5000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254712345678"}'

# Verify OTP (check console/logs for code)
curl -X POST http://localhost:5000/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254712345678", "otp_code": "123456"}'
# Save the access_token from response
```

### 4. Run Test Script
```bash
export TOKEN="your-access-token-here"
./test_phase2_endpoints.sh
```

## 📝 Manual Tests

### Test Fee Calculation
```bash
curl -X POST http://localhost:5000/api/v1/fees/calculate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "community_id": 1}' | jq
```

**Expected**: Fee breakdown showing 1.5% total (0.5% each)

### Test Transaction Limits
```bash
# Should pass
curl -X POST http://localhost:5000/api/v1/fees/validate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50000}' | jq

# Should fail (below minimum)
curl -X POST http://localhost:5000/api/v1/fees/validate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5}' | jq
```

### Test CDF
```bash
# Get CDF balance
curl -X GET http://localhost:5000/api/v1/communities/1/cdf \
  -H "Authorization: Bearer $TOKEN" | jq

# Get impact metrics
curl -X GET http://localhost:5000/api/v1/communities/1/cdf/impact \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Test Multi-Sig
```bash
# Create approval
curl -X POST http://localhost:5000/api/v1/communities/1/approvals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "WITHDRAWAL",
    "amount": 50000,
    "destination": "+254712345678",
    "description": "Test",
    "required_signatures": 2
  }' | jq

# Sign approval (use approval_id from above)
curl -X POST http://localhost:5000/api/v1/approvals/1/sign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"signature_type": "APPROVE"}' | jq
```

### Test QR Code
```bash
curl -X GET "http://localhost:5000/api/v1/checkout/qr?amount=1000&campaign_id=1" | jq
```

### Test Checkout Page
Open in browser:
```
http://localhost:5000/checkout?amount=1000&memo=Test&campaign_id=1
```

## ✅ Checklist

- [ ] Database migration successful
- [ ] All tables created
- [ ] Fee calculation works
- [ ] Transaction limits enforced
- [ ] CDF operations work
- [ ] Multi-sig approval flow works
- [ ] QR code generates
- [ ] Checkout page loads

## ⚠️ Known Limitations

1. **User.role field missing**: Admin check uses community admin status as workaround
2. **Fees not yet deducted**: Fee calculation works but fees aren't deducted from transfers yet
3. **Platform wallets**: Need to be created manually or via migration
4. **Provider credentials**: Need to be configured for live testing

## 🐛 Troubleshooting

### "Table doesn't exist" error
Run: `flask db upgrade`

### "User not found" error
Create a user first via OTP registration

### "Community not found" error
Create a community first via `/api/v1/communities`

### "Admin access required" error
User must be admin/treasurer of at least one community

## 📚 Full Documentation

See `PHASE2_REVIEW_AND_TESTING.md` for comprehensive testing guide.

