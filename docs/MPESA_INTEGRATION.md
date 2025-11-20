# M-Pesa Integration Guide

This document describes the M-Pesa (Daraja API) integration implementation.

## Structure

The M-Pesa integration is organized into modular components:

### Core Modules

1. **`services/providers/mpesa/auth.py`** - Handles Daraja API authentication
   - `MpesaAuth` class for access token generation and management
   - Automatic token caching and refresh

2. **`services/providers/mpesa/stk_push.py`** - STK Push (Lipa na M-Pesa Online)
   - `MpesaSTKPush` class for initiating STK Push payments
   - Phone number formatting
   - Password generation for API requests
   - Status query functionality

3. **`services/providers/mpesa/c2b.py`** - Customer to Business (C2B) payments
   - `MpesaC2B` class for C2B URL registration
   - Validation and confirmation callback parsing
   - C2B payment simulation (for sandbox testing)

4. **`services/providers/mpesa/b2c.py`** - Business to Customer (B2C) payouts
   - `MpesaB2C` class for initiating B2C payouts
   - Result and queue timeout callback parsing
   - Supports SalaryPayment, BusinessPayment, and PromotionPayment

5. **`services/providers/mpesa.py`** - Main adapter
   - `MpesaAdapter` class implementing `ProviderAdapter` interface
   - Integrates with `ProviderService` for unified payment processing
   - Handles webhook parsing for STK and C2B callbacks

### Routes

**`routes/mpesa_routes.py`** - Flask API endpoints:

- `POST /api/v1/mpesa/pay` - Initiate STK Push payment (requires JWT)
- `POST /api/v1/mpesa/callback` - Handle STK Push callback (public)
- `POST /api/v1/mpesa/confirmation` - Handle C2B confirmation (public)
- `POST /api/v1/mpesa/validation` - Handle C2B validation (public)

## Configuration

Add these environment variables to your `.env` file:

```bash
# M-Pesa (Daraja) Credentials
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=your_shortcode
MPESA_BASE_URL=https://sandbox.safaricom.co.ke  # or https://api.safaricom.co.ke for production

# Callback URLs
MPESA_CALLBACK_URL=https://your-domain.com/api/v1/mpesa/callback
MPESA_C2B_VALIDATION_URL=https://your-domain.com/api/v1/mpesa/validation
MPESA_C2B_CONFIRMATION_URL=https://your-domain.com/api/v1/mpesa/confirmation
MPESA_C2B_RESPONSE_TYPE=Completed

# B2C Configuration (for payouts)
MPESA_INITIATOR_NAME=your_initiator_name
MPESA_SECURITY_CREDENTIAL=your_encrypted_security_credential
MPESA_B2C_QUEUE_TIMEOUT_URL=https://your-domain.com/api/v1/mpesa/b2c/queue-timeout
MPESA_B2C_RESULT_URL=https://your-domain.com/api/v1/mpesa/b2c/result
```

## Usage

### STK Push Payment

**Initiate a payment:**

```bash
POST /api/v1/mpesa/pay
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "phone": "254712345678",
  "amount": 100.00,
  "account_reference": "PAY-12345",
  "transaction_desc": "Payment for services"
}
```

**Response:**
```json
{
  "success": true,
  "payment_id": 123,
  "checkout_request_id": "ws_CO_123456789",
  "customer_message": "Success. Request accepted for processing",
  "merchant_request_id": "12345-67890-1",
  "response_code": "0"
}
```

**Note**: A Payment record is automatically created before initiating the STK Push. The `payment_id` can be used to track the payment status. If you're authenticated, the payment will be linked to your wallet. If not authenticated, the payment will still be tracked but won't be credited to a wallet until you link it.

The customer will receive an STK Push prompt on their phone. The payment result will be sent to the callback URL, and the Payment record will be updated accordingly.

### C2B URL Registration

To enable C2B payments, register your URLs with M-Pesa:

```python
from services.providers.mpesa.c2b import MpesaC2B

c2b = MpesaC2B()
result = c2b.register_urls(
    validation_url="https://your-domain.com/api/v1/mpesa/validation",
    confirmation_url="https://your-domain.com/api/v1/mpesa/confirmation"
)
```

### Integration with ProviderService

The M-Pesa adapter is automatically registered with `ProviderService`:

```python
from services.provider_service import ProviderService

provider_service = ProviderService()
adapter = provider_service.get_adapter("MPESA")

# Initiate STK Push
result = adapter.initiate_debit(
    phone="254712345678",
    amount=Decimal("100.00"),
    currency="KES",
    reference="PAY-12345"
)
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

Common error codes:
- `MISSING_PHONE` - Phone number not provided
- `MISSING_AMOUNT` - Amount not provided
- `MISSING_REFERENCE` - Account reference not provided
- `INVALID_AMOUNT` - Invalid amount format or value
- `STK_PUSH_FAILED` - STK Push initiation failed
- `INTERNAL_ERROR` - Unexpected server error

## Webhook Handling

### STK Push Callback

M-Pesa sends callbacks to `/api/v1/mpesa/callback` when:
- Customer completes payment
- Customer cancels payment
- Payment times out

The callback is also processed by the existing webhook handler at `/api/v1/webhooks/provider/MPESA` which integrates with the payment system.

### C2B Callbacks

- **Validation**: Called before processing C2B payment. Return `ResultCode: 0` to accept, non-zero to reject.
- **Confirmation**: Called after C2B payment is processed. Use this to update payment status and credit wallets.

## Extensibility

The module is designed to be easily extended:

1. **B2C (Business to Customer)**: Add `b2c.py` module and implement in `MpesaAdapter.payout()`
2. **Transaction Status Query**: Add `transaction_status.py` module
3. **Account Balance**: Add `account_balance.py` module
4. **Reversal**: Add reversal functionality to `MpesaAdapter.refund()`

All modules follow the same pattern:
- Use `MpesaAuth` for authentication
- Return consistent response dictionaries
- Include proper error handling and logging

## Testing

### Sandbox Testing

1. Get sandbox credentials from [Safaricom Developer Portal](https://developer.safaricom.co.ke)
2. Use test phone numbers: `254708374149` (always accepts), `254708374149` (always rejects)
3. Set `MPESA_BASE_URL=https://sandbox.safaricom.co.ke`

### Local Development

For local testing, use ngrok to expose your callback URLs:

```bash
ngrok http 5000
# Update MPESA_CALLBACK_URL with ngrok URL
```

## Security Notes

1. **Never commit credentials** - Use environment variables
2. **Use HTTPS** - M-Pesa requires HTTPS for production callbacks
3. **Validate callbacks** - Verify callback authenticity (implement signature validation)
4. **Rate limiting** - Consider rate limiting on payment endpoints
5. **Idempotency** - Use unique references to prevent duplicate payments

### B2C Payout

**Initiate a payout:**

```bash
POST /api/v1/payouts
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "from_wallet": 123,
  "method": "MOMO",
  "destination": "254712345678",
  "amount": 1000.00,
  "currency": "KES",
  "provider": "MPESA",
  "description": "Payment for services"
}
```

**Response:**
```json
{
  "success": true,
  "payment_id": 456,
  "status": "PENDING",
  "provider_ref": "abc123-def456-ghi789"
}
```

The payout will be processed via M-Pesa B2C API. The result will be sent to the B2C result callback URL.

## Next Steps

- [x] Implement B2C (Business to Customer) payouts
- [ ] Add transaction status query API
- [ ] Implement account balance API
- [ ] Add callback signature validation
- [ ] Add comprehensive unit tests
- [ ] Add integration tests with sandbox

