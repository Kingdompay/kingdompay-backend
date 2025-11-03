# Phase 2: Transaction Fees and Community Contributions

## Overview

KingdomPay implements a **fee and contribution system** that recycles value back into the community economy, creating a self-sustaining financial ecosystem.

## Transaction Fees (1.5% Total)

Every transaction is subject to a **1.5% transaction fee**, split three ways:

- **0.5%** → Platform maintenance and developer support (sustainability)
- **0.5%** → Local community operational pool (if community transaction)
- **0.5%** → Federal/national community reserve (scaling and interoperability)

### Fee Allocation

Fees are automatically calculated and allocated during transfer operations:
- Fees are deducted from the transaction amount
- Platform fees go to a system wallet
- Community fees go to the originating community's operational wallet
- Federal fees go to the national reserve wallet

## Community Contributions (1% Default, Configurable)

Beyond transaction fees, there's a **voluntary-but-default community contribution** of **1%** (configurable per community) that goes to **Community Development Funds (CDFs)**.

### CDF Allocation

CDFs are divided into:
- **Education** - School bursaries, scholarships
- **Health** - Medical support, health initiatives
- **Welfare** - Social support, emergency funds
- **General** - Flexible community projects

### Impact Tracking

Communities can see real-time impact metrics:
- Total contributions (30 days, all-time)
- Estimated bursaries funded
- Estimated health supports provided
- Allocation breakdown (Education/Health/Welfare/General)

## Transaction Limits

### Per Transaction
- **Minimum**: KSh 10 (enables micro-payments)
- **Maximum**: KSh 500,000 (regulatory compliance)

### Daily Limits (by KYC Tier)
- **Tier 0** (Phone Verified): KSh 50,000/day
- **Tier 1** (ID Verified): KSh 500,000/day
- **Tier 2** (Enhanced): KSh 1,000,000/day

### Community Contributions
- No upper limit on contributions
- Rate adjustable by community councils (default 1%, max 10%)

## Multi-Signature Controls

Community wallets operate under **multi-signature authorization**:

### Ownership
- Community wallets belong to the **community**, not individuals
- Managed by **Community Admin Council (CAC)** - typically 3-5 trusted signatories

### Operations Requiring Approval
- Withdrawals
- Payouts to external accounts
- Disbursements for projects

### Approval Process
1. Request created by admin/treasurer
2. Requires 2+ signatures (configurable, typically 2 of 3-5)
3. Real-time transaction visibility for all members
4. Blockchain-style audit logging

## API Endpoints

### Fee Calculation
```
POST /api/v1/fees/calculate
{
  "amount": 1000,
  "community_id": 123  # optional
}
```

### Validate Limits
```
POST /api/v1/fees/validate-limits
{
  "amount": 50000
}
```

### CDF Information
```
GET /api/v1/communities/{id}/cdf
GET /api/v1/communities/{id}/cdf/impact
```

### Update Contribution Rate
```
PUT /api/v1/communities/{id}/cdf/contribution-rate
{
  "contribution_rate": 0.02  # 2%
}
```

### Multi-Signature Approvals
```
POST /api/v1/communities/{id}/approvals
POST /api/v1/approvals/{id}/sign
GET /api/v1/approvals/{id}
POST /api/v1/approvals/{id}/execute
```

## Implementation Notes

### Fee Deduction Flow
1. User initiates transfer of amount X
2. System validates limits
3. Calculates fees (1.5% of X)
4. Calculates contribution (1% of X if community transaction)
5. Net amount = X - fees - contribution
6. Transfer net amount to recipient
7. Allocate fees to respective wallets
8. Allocate contribution to CDF

### Community Transaction Detection
- Transaction is "community" if either wallet is owned by a community
- Fees and contributions apply based on originating wallet ownership

### Platform Wallets
- Platform wallet (owner_type="PLATFORM", owner_id=0) receives platform fees
- Federal reserve wallet receives federal fees
- Community operational wallets receive community fees

## Database Models

### TransactionFee
- Tracks fee allocation per transaction
- Links to journal_id and payment_id
- Stores breakdown (platform, community, federal)

### CommunityContribution
- Tracks CDF contributions
- Links to journal_id, payment_id, community_id
- Stores allocation (Education/Health/Welfare/General)

### CommunityDevelopmentFund
- Stores CDF balances per community
- Tracks total contributions
- Configurable contribution rate

### MultiSigApproval
- Approval requests for community operations
- Tracks required vs received signatures
- Status: PENDING → APPROVED → EXECUTED

### MultiSigSignature
- Individual signatures on approvals
- Tracks who signed and when
- IP address and user agent for audit

## Security Considerations

- All fee calculations use Decimal for precision
- Multi-sig requires admin/treasurer role
- Approval requests are immutable after execution
- Fee allocation creates separate ledger entries for audit
- Limits enforced at API and service layers

## Future Enhancements

- Dynamic fee rates based on transaction size
- Community-voted fee adjustments
- Impact dashboard with real stories
- Integration with external impact measurement tools
- Blockchain-based immutable audit trail

