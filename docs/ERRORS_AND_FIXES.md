# KingdomPay Backend - Errors and Fixes

## Critical Issues Found

### 1. OTP Service Bug - CRITICAL

**Location**: `services/auth_service.py:65`

**Issue**: The `send_otp` method tries to access `otp.otp_code` but the `generate_otp` method in `models/otp.py` doesn't return the OTP code.

**Current Code**:

```python
# In auth_service.py line 65
message = f"Your KingdomPay verification code is: {otp.otp_code}. Valid for 5 minutes."
```

**Problem**: The `OTPVerification.generate_otp()` method returns an OTP object but doesn't expose the `otp_code` attribute.

**Fix Required**:

```python
# In models/otp.py, modify the generate_otp method:
@classmethod
def generate_otp(cls, phone_number, expiry_minutes=5):
    """Generate a new OTP for phone number"""
    # Generate 6-digit OTP
    otp_code = "".join(random.choices(string.digits, k=6))

    # Set expiry time
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    # Create OTP record
    otp = cls(
        phone_number=phone_number,
        otp_hash=generate_password_hash(otp_code),
        expires_at=expires_at,
    )

    db.session.add(otp)
    db.session.commit()

    # Add the otp_code as an attribute for immediate use
    otp.otp_code = otp_code
    return otp
```

### 2. Missing Wallet Creation - CRITICAL

**Location**: `services/auth_service.py:100-107`

**Issue**: When creating a new user, no wallet is automatically created. The wallet routes expect a wallet to exist.

**Current Code**:

```python
# Create new user
user = User(
    full_name=full_name,
    phone_number=validated_phone,
    is_phone_verified=True,
)
db.session.add(user)
db.session.commit()
```

**Fix Required**:

```python
# Create new user
user = User(
    full_name=full_name,
    phone_number=validated_phone,
    is_phone_verified=True,
)
db.session.add(user)
db.session.flush()  # Get user ID

# Create wallet for new user
from models.wallet import Wallet
wallet = Wallet(user_id=user.id)
db.session.add(wallet)
db.session.commit()
```

### 3. Incomplete Ledger Service - HIGH

**Location**: `services/ledger_service.py`

**Issue**: The LedgerService has placeholder implementations with TODO comments.

**Missing Implementations**:

- `create_transaction()` - Returns placeholder response
- `get_transaction_history()` - Returns empty list
- `validate_transaction()` - Always returns True

**Fix Required**: Implement proper ledger functionality or remove unused service.

### 4. Missing Transfer Endpoints - HIGH

**Location**: `api/v1/wallet_routes.py`

**Issue**: No endpoints for wallet-to-wallet transfers, deposits, or withdrawals.

**Missing Endpoints**:

- `POST /api/v1/wallets/transfer` - Transfer between wallets
- `POST /api/v1/wallets/deposit` - Add funds to wallet
- `POST /api/v1/wallets/withdraw` - Remove funds from wallet

### 5. Wallet Display Number Generation - MEDIUM

**Location**: `models/wallet.py:25`

**Issue**: The `display_number` field is defined but never populated.

**Current Code**:

```python
display_number = db.Column(db.String(20), unique=True)
```

**Fix Required**: Generate display number when creating wallet:

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if not self.display_number:
        self.display_number = f"WAL-{random.randint(100000000, 999999999)}"
```

## Minor Issues

### 1. Error Handling Inconsistency

**Location**: Multiple files

**Issue**: Some endpoints return different error message formats.

**Fix**: Standardize error response format across all endpoints.

### 2. Missing Input Validation

**Location**: `api/v1/wallet_routes.py`

**Issue**: No validation for pagination parameters.

**Fix**: Add validation for page and per_page parameters.

### 3. Missing Transaction Types

**Location**: `models/transaction.py`

**Issue**: Only basic transaction types are supported.

**Missing Types**:

- `TRANSFER` - Wallet to wallet transfer
- `FEE` - Transaction fees
- `REFUND` - Refund transactions

## Security Issues

### 1. OTP Storage

**Location**: `models/otp.py`

**Issue**: OTP codes are hashed but the original code is not immediately available for SMS.

**Current**: OTP is hashed and stored, but SMS needs the plain text.

**Fix**: Store plain text temporarily or modify the flow to generate OTP, send SMS, then hash.

### 2. Rate Limiting

**Location**: `api/v1/auth_routes.py`

**Issue**: Rate limiting is applied but may not be sufficient for production.

**Recommendation**: Implement more granular rate limiting per phone number.

## Database Issues

### 1. Missing Indexes

**Location**: Database schema

**Issue**: Some queries may be slow without proper indexes.

**Missing Indexes**:

- `transactions.created_at` - For transaction history queries
- `transactions.reference_number` - For transaction lookups
- `otp_verifications.phone_number` - Already exists
- `otp_verifications.expires_at` - For cleanup queries

### 2. Transaction Isolation

**Location**: `models/wallet.py`

**Issue**: Wallet balance updates and transaction creation should be atomic.

**Fix**: Use database transactions for balance updates.

## Performance Issues

### 1. N+1 Queries

**Location**: `api/v1/wallet_routes.py`

**Issue**: Getting user and then wallet separately.

**Fix**: Use joins or eager loading.

### 2. Missing Caching

**Location**: Multiple locations

**Issue**: No caching for frequently accessed data.

**Recommendations**:

- Cache user information
- Cache wallet balances
- Cache transaction history

## Configuration Issues

### 1. Missing Environment Variables

**Location**: `config.py`

**Issue**: Some configuration values don't have defaults.

**Missing Defaults**:

- `SMS_SENDER_ID` - Has default but not documented
- `LOG_LEVEL` - Has default
- `PROMETHEUS_PORT` - Has default

### 2. Development vs Production

**Location**: `config.py`

**Issue**: SQLite is allowed in development but may cause issues.

**Recommendation**: Use PostgreSQL even in development for consistency.

## Testing Issues

### 1. Missing Tests

**Location**: `test_auth.py`

**Issue**: Only basic auth tests exist.

**Missing Tests**:

- Wallet operations
- Transaction handling
- Error scenarios
- Rate limiting
- OTP validation

### 2. Test Database

**Location**: `config.py`

**Issue**: Test configuration uses in-memory SQLite.

**Recommendation**: Use separate test database.

## Deployment Issues

### 1. Missing Docker Configuration

**Location**: Root directory

**Issue**: No Dockerfile or docker-compose.yml for the application.

**Recommendation**: Create Docker configuration for easy deployment.

### 2. Missing Health Checks

**Location**: `app.py`

**Issue**: Basic health check exists but doesn't verify dependencies.

**Fix**: Add database and Redis connectivity checks.

## Recommended Fix Priority

### Critical (Fix Immediately)

1. OTP Service Bug - Prevents SMS sending
2. Missing Wallet Creation - Breaks wallet endpoints

### High (Fix Soon)

3. Incomplete Ledger Service - Core functionality missing
4. Missing Transfer Endpoints - Core wallet functionality

### Medium (Fix When Possible)

5. Wallet Display Number Generation
6. Error Handling Inconsistency
7. Missing Input Validation

### Low (Fix Later)

8. Performance optimizations
9. Additional tests
10. Documentation improvements

## Implementation Notes

### For OTP Fix

The OTP fix requires careful consideration of security. The current approach of hashing OTPs is good for storage, but we need the plain text for SMS. Consider:

1. Generate OTP, send SMS, then hash and store
2. Or store plain text temporarily and clean up after expiry

### For Wallet Creation

The wallet creation should be automatic when a user is created. This can be done:

1. In the auth service after user creation
2. Using database triggers (as shown in SQL files)
3. Using SQLAlchemy events

### For Transfer Endpoints

Transfer endpoints should include:

1. Validation of source and destination wallets
2. Balance checks
3. Transaction recording
4. Proper error handling
5. Rate limiting

## Testing the Fixes

After implementing fixes, test:

1. OTP flow end-to-end
2. Wallet creation for new users
3. Wallet operations (balance, transactions)
4. Error scenarios
5. Rate limiting
6. Database integrity

## Monitoring

After fixes are deployed, monitor:

1. OTP delivery rates
2. Wallet creation success rates
3. Transaction processing times
4. Error rates
5. Database performance
