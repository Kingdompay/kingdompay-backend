# Phase 2 Integration Checklist

## Overview

This document lists all items that need to be integrated before Phase 2 is production-ready. Currently, fees, contributions, and multi-sig systems are **built and tested** but **not yet integrated** into the transfer/payment flows.

---

## 🔴 CRITICAL: Fee Integration into Transfers

### Current State

- ✅ Fee calculation service works (`FeeService.calculate_fees()`)
- ✅ Fee allocation methods exist (`FeeService.allocate_fees()`)
- ✅ Transaction limit validation works
- ❌ **Fees are NOT deducted from transfers**
- ❌ **Community contributions are NOT deducted**
- ❌ **Fees are NOT allocated to platform/community/federal wallets**

### What Needs Integration

#### 1. Update `create_transfer()` in `wallet_routes.py`

**Location**: `api/v1/wallet_routes.py:104`

**Current Flow**:

```
User requests transfer → Validate → Post ledger entry → Done
```

**Required Flow**:

```
User requests transfer →
  Validate transaction limits →
  Calculate fees (1.5%) →
  Calculate community contribution (1% if applicable) →
  Validate sufficient balance (amount + fees + contribution) →
  Post main transfer journal →
  Post fee allocation journals →
  Post contribution allocation journal →
  Create TransactionFee record →
  Create CommunityContribution record →
  Update platform/community/federal wallet balances →
  Done
```

**Code Changes Needed**:

- Import `FeeService` and `RiskService`
- Call `fee_service.validate_transaction_limits()` before transfer
- Calculate fees and contributions
- Check balance includes: `amount + fees + contributions`
- Create separate ledger journals for:
  - Main transfer (source → destination)
  - Platform fee allocation (source → platform wallet)
  - Community fee allocation (source → community wallet, if applicable)
  - Federal fee allocation (source → federal wallet)
  - Contribution allocation (source → CDF wallet, if applicable)
- Call `fee_service.allocate_fees()` and `fee_service.allocate_contribution()`
- Return fee breakdown in response

#### 2. Update `post_transfer()` in `ledger_service.py`

**Location**: `services/ledger_service.py:186`

**Enhancement Needed**:

- Accept optional `fee_breakdown` parameter
- Create additional journal entries for fee allocation
- Return fee information in result

**OR** (Better approach):

- Keep `post_transfer()` simple (just the main transfer)
- Create separate `post_fee_allocation()` method
- Call from wallet routes after main transfer

#### 3. Update `transfer_funds()` in `wallet_routes.py`

**Location**: `api/v1/wallet_routes.py:163`

**Same integration needed** as `create_transfer()`

---

## 🔴 CRITICAL: Multi-Signature Integration into Payouts

### Current State

- ✅ Multi-sig service works (`MultiSigService`)
- ✅ Approval creation and signing works
- ❌ **Payouts do NOT require multi-sig approval**
- ❌ **Payouts execute immediately without approval**

### What Needs Integration

#### Update `create_payout()` in `payouts_routes.py`

**Location**: `api/v1/payouts_routes.py:22`

**Current Flow**:

```
Treasurer requests payout → Validate → Execute immediately → Done
```

**Required Flow**:

```
Treasurer requests payout →
  Create MultiSigApproval request →
  Return approval_id (status: PENDING) →
  [Other admins sign approval] →
  When approved → Execute payout →
  Update approval status to EXECUTED →
  Done
```

**Code Changes Needed**:

- Import `MultiSigService`
- Check if wallet is community wallet (`owner_type == "COMMUNITY"`)
- If community wallet:
  - Create approval request via `multisig_service.create_approval_request()`
  - Don't execute payout immediately
  - Return approval_id for tracking
  - Provide endpoint to check approval status
- If not community wallet (personal):
  - Execute immediately (no multi-sig required)
- Add new endpoint: `POST /api/v1/payouts/{approval_id}/execute`
  - Check if approval status is "APPROVED"
  - Execute payout
  - Update approval to "EXECUTED"

---

## 🟡 IMPORTANT: Platform & Federal Wallet Creation

### Current State

- ✅ Platform wallet creation logic exists in `FeeService.allocate_fees()`
- ✅ Wallet model supports `owner_type="PLATFORM"` and `owner_type="FEDERAL"`
- ❌ **Platform wallets don't exist in database**
- ❌ **Federal wallet doesn't exist**

### What Needs Integration

#### Create Initialization Script/Migration

**File to Create**: `scripts/create_system_wallets.py` or add to migration

**Code Needed**:

```python
def create_system_wallets():
    """Create platform and federal wallets if they don't exist"""
    # Platform wallet (receives platform fees)
    platform_wallet = Wallet.query.filter_by(
        owner_type="PLATFORM",
        owner_id=0
    ).first()

    if not platform_wallet:
        platform_wallet = Wallet(
            owner_type="PLATFORM",
            owner_id=0,
            currency="KES",
            balance=Decimal("0"),
            display_number="PLATFORM001"  # or generate
        )
        db.session.add(platform_wallet)

    # Federal wallet (receives federal fees)
    federal_wallet = Wallet.query.filter_by(
        owner_type="FEDERAL",
        owner_id=0
    ).first()

    if not federal_wallet:
        federal_wallet = Wallet(
            owner_type="FEDERAL",
            owner_id=0,
            currency="KES",
            balance=Decimal("0"),
            display_number="FEDERAL001"
        )
        db.session.add(federal_wallet)

    db.session.commit()
```

**Where to Call**:

- In application startup (`app.py`)
- Or in database migration
- Or in setup script

---

## 🟡 IMPORTANT: Community Wallet Detection

### Current State

- ✅ Wallet model has `owner_type` field
- ✅ Can be "USER", "COMMUNITY", "PLATFORM", "FEDERAL"
- ❌ **Transfer logic doesn't detect community wallets**
- ❌ **Fees not applied based on wallet ownership**

### What Needs Integration

#### Update Fee Calculation Logic

**Location**: `api/v1/wallet_routes.py` (transfer endpoints)

**Code Needed**:

```python
# Detect if transaction involves community
to_wallet = Wallet.query.get(to_wallet_id)
community_id = None

if from_wallet.owner_type == "COMMUNITY":
    community_id = from_wallet.owner_id
elif to_wallet.owner_type == "COMMUNITY":
    community_id = to_wallet.owner_id

# Calculate fees with community_id
fee_breakdown = fee_service.calculate_fees(amount, community_id=community_id)

# Calculate contribution if community involved
contribution_breakdown = None
if community_id:
    contribution_breakdown = fee_service.calculate_contribution(amount, community_id)
```

---

## 🟡 IMPORTANT: Ledger Entries for Fee Allocation

### Current State

- ✅ Main transfer creates ledger journal and entries
- ✅ Fee service has `allocate_fees()` method
- ❌ **Fee allocation doesn't create ledger entries**
- ❌ **Fees are recorded but not moved to fee wallets**

### What Needs Integration

#### Create Fee Allocation Journal Entries

**Location**: Create new method in `ledger_service.py` or update `FeeService`

**Code Structure**:

```python
def post_fee_allocation(self, journal_id, fee_breakdown, from_wallet_id):
    """Create ledger entries for fee allocation"""
    # Platform fee entry
    platform_entry = LedgerEntry(
        journal_id=journal_id,
        wallet_id=platform_wallet_id,
        account_code="PLATFORM_FEES",
        debit=fee_breakdown["platform_fee"],
        credit=Decimal("0"),
    )

    # Community fee entry (if applicable)
    # Federal fee entry

    # Deduct from source wallet
    source_fee_entry = LedgerEntry(
        journal_id=journal_id,
        wallet_id=from_wallet_id,
        account_code="FEES_PAYABLE",
        debit=Decimal("0"),
        credit=fee_breakdown["fee_amount"],
    )
```

---

## 🟢 NICE TO HAVE: Campaign Contribution Integration

### Current State

- ✅ Campaign model exists
- ✅ Contribution model exists
- ✅ Contribution tracking works
- ❌ **Campaign contributions don't trigger community contributions**
- ❌ **Contributions to campaigns don't show in CDF**

### What Needs Integration

#### Update Campaign Contribution Endpoint

**Location**: `api/v1/campaigns_routes.py`

**Enhancement**:

- When contributing to campaign:
  - Deduct 1% community contribution automatically
  - Allocate to CDF
  - Show contribution in campaign progress

---

## 🟢 NICE TO HAVE: Risk Checks in Transfers

### Current State

- ✅ Risk service exists (`RiskService`)
- ✅ Velocity limits work
- ✅ Blacklist checks work
- ❌ **Risk checks not called in transfer flow**

### What Needs Integration

#### Add Risk Validation

**Location**: `api/v1/wallet_routes.py` (transfer endpoints)

**Code Needed**:

```python
# Check blacklist
if risk_service.check_blacklist("PHONE", destination_phone):
    return jsonify({"success": False, "message": "Destination is blacklisted"}), 400

# Check velocity limits
velocity_check = risk_service.check_velocity_limits(
    user_id=user.id,
    wallet_id=from_wallet.id,
    amount=amount,
)
if not velocity_check["allowed"]:
    return jsonify({"success": False, "message": velocity_check["reason"]}), 400

# Check transaction risk
risk_check = risk_service.check_transaction_risk(
    user_id=user.id,
    wallet_id=from_wallet.id,
    amount=amount,
    destination=destination,
)
if not risk_check["allowed"]:
    # Maybe create AML case for high-risk
    if risk_check["risk_score"] >= 80:
        risk_service.create_aml_case(user.id, "HIGH_RISK", {...})
    return jsonify({"success": False, "message": "Transaction blocked"}), 400
```

---

## 📋 Integration Priority

### 🔴 Priority 1 (Must Have for Production)

1. **Fee Integration into Transfers** - Core revenue model
2. **Multi-Sig Integration into Payouts** - Security requirement
3. **Platform/Federal Wallet Creation** - Required for fee collection

### 🟡 Priority 2 (Important)

4. **Community Wallet Detection** - Proper fee application
5. **Ledger Entries for Fee Allocation** - Audit trail

### 🟢 Priority 3 (Nice to Have)

6. **Risk Checks in Transfers** - Enhanced security
7. **Campaign Contribution Integration** - Feature enhancement

---

## 🧪 Testing After Integration

For each integration, create/update tests:

1. **Test fee deduction from transfer**

   - Transfer KSh 1,000
   - Verify fees deducted (KSh 15 if community, KSh 10 if not)
   - Verify platform/federal wallet balances updated
   - Verify TransactionFee record created

2. **Test multi-sig payout**

   - Create payout request
   - Verify approval required
   - Sign by 2 admins
   - Verify payout executed

3. **Test community contribution**

   - Transfer to community wallet
   - Verify 1% contribution deducted
   - Verify CDF balance updated
   - Verify CommunityContribution record created

4. **Test transaction limits**
   - Attempt transfer below minimum (should fail)
   - Attempt transfer above maximum (should fail)
   - Attempt transfer exceeding daily limit (should fail)

---

## 📝 Summary

**Total Integration Points**: 7

- 🔴 Critical: 3
- 🟡 Important: 2
- 🟢 Nice to Have: 2

**Estimated Effort**:

- Priority 1: 4-6 hours
- Priority 2: 2-3 hours
- Priority 3: 2-3 hours

**Ready to Start**: Yes, all infrastructure is in place!

---

**Next Step**: Start with Priority 1 items. Begin with fee integration into transfers.
