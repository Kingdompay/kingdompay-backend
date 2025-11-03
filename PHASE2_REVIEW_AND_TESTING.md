# Phase 2 Review and Testing Guide

## 🔍 Code Review Summary

### ✅ Model Registration
All new models are properly imported in `models/__init__.py`:
- ✅ TransactionFee
- ✅ CommunityContribution  
- ✅ CommunityDevelopmentFund
- ✅ MultiSigApproval
- ✅ MultiSigSignature
- ✅ Blacklist
- ✅ AMLCase
- ✅ SettlementBatch (already existed)

### ✅ Import Structure
- All models use proper relative imports
- Services import models correctly
- No circular dependencies detected

### ⚠️ Migration Required
New database tables need to be created. Run:
```bash
flask db migrate -m "Add Phase 2 models: fees, multisig, risk"
flask db upgrade
```

## 📋 Pre-Testing Checklist

### 1. Database Migration
```bash
cd kingdompay-backend
flask db migrate -m "Phase 2: Add fees, multisig, risk models"
flask db upgrade
```

Verify tables created:
- `transaction_fees`
- `community_contributions`
- `community_development_funds`
- `multisig_approvals`
- `multisig_signatures`
- `blacklists`
- `aml_cases`

### 2. Environment Variables

Verify these are set (or have defaults):
```bash
# M-Pesa
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_PASSKEY=
MPESA_SHORTCODE=
MPESA_INITIATOR_NAME=          # For B2C
MPESA_SECURITY_CREDENTIAL=     # For B2C
MPESA_BASE_URL=https://sandbox.safaricom.co.ke
MPESA_CALLBACK_URL=https://your-domain.com/api/v1/webhooks/provider/mpesa
MPESA_B2C_CALLBACK_URL=

# Airtel Money
AIRTEL_CLIENT_ID=
AIRTEL_CLIENT_SECRET=
AIRTEL_BASE_URL=https://openapiuat.airtel.africa
AIRTEL_CALLBACK_URL=

# T-Kash
TKASH_API_KEY=
TKASH_API_SECRET=
TKASH_MERCHANT_ID=
TKASH_BASE_URL=https://api.t-kash.co.ke
TKASH_CALLBACK_URL=
```

### 3. Dependencies Check

Verify all required packages:
```bash
pip install qrcode Pillow  # For QR generation (already in requirements.txt)
```

## 🧪 Testing Guide

### Test 1: Fee Calculation API

**Endpoint**: `POST /api/v1/fees/calculate`

```bash
# Get JWT token first
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+254712345678","otp_code":"123456"}' | jq -r '.access_token')

# Test fee calculation
curl -X POST http://localhost:5000/api/v1/fees/calculate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "community_id": 1
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "fees": {
    "transaction_amount": 1000.0,
    "fee_amount": 15.0,
    "platform_fee": 5.0,
    "community_fee": 5.0,
    "federal_fee": 5.0,
    "net_amount": 985.0
  }
}
```

### Test 2: Transaction Limits Validation

**Endpoint**: `POST /api/v1/fees/validate-limits`

```bash
curl -X POST http://localhost:5000/api/v1/fees/validate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50000}'
```

**Expected Response**:
```json
{
  "allowed": true
}
```

Test minimum limit:
```bash
curl -X POST http://localhost:5000/api/v1/fees/validate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5}'
```

**Expected Response**:
```json
{
  "allowed": false,
  "message": "Minimum transaction amount is KSh 10"
}
```

### Test 3: CDF Operations

**Get CDF Balance**:
```bash
curl -X GET http://localhost:5000/api/v1/communities/1/cdf \
  -H "Authorization: Bearer $TOKEN"
```

**Get CDF Impact Metrics**:
```bash
curl -X GET http://localhost:5000/api/v1/communities/1/cdf/impact \
  -H "Authorization: Bearer $TOKEN"
```

**Update Contribution Rate** (Admin only):
```bash
curl -X PUT http://localhost:5000/api/v1/communities/1/cdf/contribution-rate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contribution_rate": 0.02}'
```

### Test 4: Multi-Signature Approvals

**Create Approval Request**:
```bash
curl -X POST http://localhost:5000/api/v1/communities/1/approvals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "WITHDRAWAL",
    "amount": 50000,
    "destination": "+254712345678",
    "description": "Project disbursement",
    "required_signatures": 2
  }'
```

**Sign Approval** (as different admin):
```bash
APPROVAL_ID=1  # From previous response

curl -X POST http://localhost:5000/api/v1/approvals/$APPROVAL_ID/sign \
  -H "Authorization: Bearer $OTHER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"signature_type": "APPROVE"}'
```

**Get Approval Status**:
```bash
curl -X GET http://localhost:5000/api/v1/approvals/$APPROVAL_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Execute Approved Request**:
```bash
curl -X POST http://localhost:5000/api/v1/approvals/$APPROVAL_ID/execute \
  -H "Authorization: Bearer $TOKEN"
```

### Test 5: Hosted Checkout

**Access Checkout Page**:
```
http://localhost:5000/checkout?amount=1000&memo=Test&campaign_id=1
```

**Generate QR Code**:
```bash
curl -X GET "http://localhost:5000/api/v1/checkout/qr?amount=1000&campaign_id=1"
```

**Initiate Payment**:
```bash
curl -X POST http://localhost:5000/api/v1/checkout/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "phone": "+254712345678",
    "provider": "MPESA",
    "campaign_id": 1
  }'
```

### Test 6: Provider Adapters

**Test Provider Listing**:
```bash
curl -X GET http://localhost:5000/api/v1/providers \
  -H "Authorization: Bearer $TOKEN"
```

**Test M-Pesa Top-up** (with sandbox credentials):
```bash
curl -X POST http://localhost:5000/api/v1/topups/momo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": 1,
    "amount": 100,
    "phone": "+254712345678",
    "provider": "MPESA"
  }'
```

### Test 7: Reconciliation (Admin)

**Manual Reconciliation**:
```bash
curl -X POST http://localhost:5000/api/v1/reconciliation/reconcile \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "MPESA",
    "statement_date": "2024-01-15",
    "provider_transactions": [
      {
        "transaction_id": "ABC123",
        "amount": 1000,
        "status": "SUCCESS",
        "timestamp": "2024-01-15T10:00:00Z"
      }
    ]
  }'
```

**Get Reconciliation Reports**:
```bash
curl -X GET "http://localhost:5000/api/v1/reconciliation/reports?provider=MPESA&start_date=2024-01-01" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 🔧 Integration Points to Verify

### 1. Wallet Model Updates
- Check if `Wallet.owner_type` supports "PLATFORM", "COMMUNITY"
- Verify wallet creation on user signup still works
- Test community wallet creation

### 2. Payment Model
- Verify `Payment` model has all required fields
- Check `provider_ref` indexing for webhook matching

### 3. Ledger Service
- Current implementation may need extension for fee allocation
- Verify double-entry principles maintained
- Check journal entries for fee transactions

### 4. Community Service
- Verify community wallet creation
- Check member role assignments (ADMIN, TREASURER)

### 5. RBAC Service
- `require_admin` decorator needs User model to have `role` field
- Verify `is_community_admin` works correctly

## ⚠️ Known Issues & TODOs

### 1. User Model Role Field
The `require_admin` decorator expects `User.role`, but User model may not have this. Options:
- Add `role` field to User model (migration needed)
- Or modify decorator to check admin status differently

### 2. Fee Integration Not Complete
Fees are calculated but NOT yet deducted from transfers. The fee service is ready, but wallet transfer routes need updating to:
- Call `fee_service.validate_transaction_limits()`
- Calculate fees before transfer
- Deduct fees from source wallet
- Allocate fees to platform/community/federal wallets
- Create TransactionFee records

### 3. Platform Wallets
Platform and federal wallets need to be created. Add to migration or initialization:
```python
# Platform wallet
platform_wallet = Wallet(
    owner_type="PLATFORM",
    owner_id=0,
    currency="KES",
    balance=Decimal("0")
)

# Federal reserve wallet
federal_wallet = Wallet(
    owner_type="FEDERAL",
    owner_id=0,
    currency="KES",
    balance=Decimal("0")
)
```

### 4. CDF Initialization
Community Development Funds are created on-demand, but may need explicit initialization for existing communities.

### 5. Multi-Sig Integration
Payout routes should check for multi-sig approval before executing. Currently payout routes don't require approval.

## 📝 Manual Testing Scenarios

### Scenario 1: Complete Transfer with Fees
1. User A has wallet with KSh 10,000
2. User A transfers KSh 1,000 to User B
3. Verify:
   - User A balance: 10,000 - 1,000 - 15 (fees) = 8,985
   - User B balance: +1,000
   - TransactionFee record created
   - Platform/Community/Federal fees allocated

### Scenario 2: Community Contribution
1. User contributes KSh 5,000 to community campaign
2. Verify:
   - KSh 50 (1%) allocated to CDF
   - CDF balance updated
   - CommunityContribution record created

### Scenario 3: Multi-Sig Withdrawal
1. Treasurer creates withdrawal approval request (KSh 50,000)
2. First admin signs approval
3. Second admin signs approval
4. Approval status becomes "APPROVED"
5. Treasurer executes approval
6. Withdrawal processed

### Scenario 4: Transaction Limits
1. Tier 0 user attempts KSh 60,000 transaction
2. Should fail with "Daily limit exceeded" message
3. Tier 2 user attempts same amount
4. Should succeed

## 🐛 Debugging Tips

### Check Database
```python
# In Flask shell
from models import *
from extensions import db

# Check if tables exist
db.engine.table_names()

# Check fee records
TransactionFee.query.all()

# Check CDF balances
CommunityDevelopmentFund.query.all()
```

### Check Logs
```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log
```

### Test Provider Adapters
```python
from services.provider_service import ProviderService

ps = ProviderService()
adapter = ps.get_adapter("MPESA")
print(adapter.list_providers())
```

## ✅ Success Criteria

Phase 2 is considered successful when:

1. ✅ All models can be created in database
2. ✅ Fee calculation API returns correct values
3. ✅ Transaction limits enforced correctly
4. ✅ CDF balances update on contributions
5. ✅ Multi-sig approvals work (create, sign, execute)
6. ✅ Checkout page renders and initiates payments
7. ✅ QR codes generate successfully
8. ✅ Provider adapters initialize without errors
9. ✅ Reconciliation service can process statements
10. ⚠️ Fees deducted from transfers (pending integration)

## 🔄 Next Steps After Testing

1. **Fix any issues found** during testing
2. **Integrate fees into transfer flow** (see PHASE2_IMPLEMENTATION_SUMMARY.md)
3. **Update payout routes** to require multi-sig approval
4. **Create platform/federal wallets** on initialization
5. **Add User.role field** or update admin decorator
6. **Initialize CDFs** for existing communities
7. **Load testing** with concurrent transactions
8. **Documentation updates** with examples

---

**Note**: Some features are ready for testing, but fee deduction from transfers is pending integration. Test what's available and we'll integrate fees next.

