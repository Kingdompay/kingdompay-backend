# Webhook Integration Guide

This guide explains how to integrate KingdomPay webhooks into your application, both for receiving provider callbacks and for sending webhooks to community endpoints.

## Provider Webhooks (Incoming)

KingdomPay receives webhooks from payment providers (M-Pesa, Airtel, T-Kash) at:

```
POST /api/v1/webhooks/provider/{PROVIDER}
```

Where `{PROVIDER}` is one of: `MPESA`, `AIRTEL`, or `TKASH`.

### Configuration

Set callback URLs in your provider dashboards:

**M-Pesa (Daraja):**
- STK Callback URL: `https://your-domain.com/api/v1/webhooks/provider/MPESA`
- B2C Callback URL: `https://your-domain.com/api/v1/webhooks/provider/MPESA`

**Airtel Money:**
- Webhook URL: `https://your-domain.com/api/v1/webhooks/provider/AIRTEL`

**T-Kash:**
- Callback URL: `https://your-domain.com/api/v1/webhooks/provider/TKASH`

### Webhook Processing

When a provider sends a webhook:

1. **Provider Adapter** parses the payload
2. **Payment** record is updated (status: PENDING → SUCCESS/FAILED)
3. **Ledger journal** is posted (if successful)
4. **Wallet balance** is updated
5. **Community webhooks** are triggered (if payment linked to campaign)

### Testing Webhooks Locally

Use ngrok or similar tunnel:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start tunnel
ngrok http 5000

# Use the https URL in provider dashboards:
# https://abc123.ngrok.io/api/v1/webhooks/provider/MPESA
```

### Webhook Payload Examples

#### M-Pesa STK Callback

```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "12345-67890-1",
      "CheckoutRequestID": "ws_CO_123456789",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 100.00},
          {"Name": "MpesaReceiptNumber", "Value": "NLJ7H7AD1R"},
          {"Name": "TransactionDate", "Value": 20240101120000},
          {"Name": "PhoneNumber", "Value": 254712345678}
        ]
      }
    }
  }
}
```

#### Airtel Money Webhook

```json
{
  "status": {
    "success": true,
    "message": "Transaction completed"
  },
  "data": {
    "transaction": {
      "id": "TXN123456",
      "amount": 100.00,
      "status": "SUCCESS"
    }
  }
}
```

### Security

- **Verify webhook signatures** (if provider supports it)
- **Use HTTPS** for all webhook endpoints
- **Implement rate limiting** on webhook endpoints
- **Log all webhook events** for audit

## Community Webhooks (Outgoing)

Communities can register webhooks to receive notifications about payment events.

### Register Webhook

```bash
POST /api/v1/webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "community_id": 123,
  "url": "https://your-community-app.com/webhooks/kingdompay",
  "secret": "your-webhook-secret"
}
```

### Webhook Events

Events are sent to registered webhooks:

#### `payment.succeeded`
```json
{
  "event_type": "payment.succeeded",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "payment_id": 456,
    "amount": 1000.00,
    "currency": "KES",
    "campaign_id": 123,
    "community_id": 45,
    "payer_phone": "+254712345678",
    "provider": "MPESA",
    "provider_ref": "NLJ7H7AD1R"
  }
}
```

#### `payment.failed`
```json
{
  "event_type": "payment.failed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "payment_id": 457,
    "amount": 500.00,
    "reason": "Insufficient funds",
    "provider": "MPESA"
  }
}
```

#### `campaign.milestone`
```json
{
  "event_type": "campaign.milestone",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "campaign_id": 123,
    "milestone": "50%",
    "current_amount": 50000.00,
    "target_amount": 100000.00
  }
}
```

#### `payout.executed`
```json
{
  "event_type": "payout.executed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "payout_id": 789,
    "amount": 5000.00,
    "destination": "+254712345678",
    "provider": "MPESA",
    "approval_id": 10
  }
}
```

### Webhook Signature Verification

All outgoing webhooks are signed with HMAC-SHA256:

```javascript
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(payload))
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

// In your webhook handler
const signature = req.headers['x-kingdompay-signature'];
const isValid = verifyWebhook(req.body, signature, process.env.WEBHOOK_SECRET);

if (!isValid) {
  return res.status(401).send('Invalid signature');
}
```

### Webhook Retry Logic

- **Retries**: 3 attempts
- **Interval**: Exponential backoff (1s, 5s, 30s)
- **Timeout**: 10 seconds per attempt
- **Dead letter**: Failed webhooks after 3 retries are logged for manual review

### Testing Community Webhooks

Use a webhook testing service:

1. **Webhook.site**: https://webhook.site - Get a unique URL, view payloads in real-time
2. **RequestBin**: https://requestbin.com - Similar to webhook.site
3. **Local tunnel**: Use ngrok to expose local server

Example:
```bash
# Start ngrok
ngrok http 3000

# Register webhook with ngrok URL
curl -X POST https://api.kingdompay.example/api/v1/webhooks \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "url": "https://abc123.ngrok.io/webhooks",
    "secret": "test-secret"
  }'

# Trigger a payment and watch webhook.site for the event
```

## Troubleshooting

### Webhook Not Received

1. **Check URL accessibility**: Ensure endpoint is publicly accessible
2. **Verify HTTPS**: Most providers require HTTPS
3. **Check firewall**: Ensure provider IPs are whitelisted (if applicable)
4. **Review logs**: Check application logs for webhook processing errors

### Webhook Received But Not Processed

1. **Check payload format**: Verify provider payload matches expected format
2. **Review adapter logs**: Check provider adapter parsing logic
3. **Verify payment exists**: Ensure payment record exists for the provider reference
4. **Check database constraints**: Ensure no foreign key or constraint violations

### Webhook Signature Verification Fails

1. **Verify secret**: Ensure `WEBHOOK_SECRET` matches what's registered
2. **Check encoding**: Ensure payload is UTF-8 encoded
3. **Verify algorithm**: Use HMAC-SHA256
4. **Check header name**: Signature should be in `X-KingdomPay-Signature` header

## Best Practices

1. **Idempotency**: Handle duplicate webhook deliveries gracefully
2. **Async processing**: Process webhooks asynchronously to avoid timeouts
3. **Logging**: Log all webhook events for audit and debugging
4. **Monitoring**: Set up alerts for webhook failure rates
5. **Versioning**: Include API version in webhook URL for future compatibility

