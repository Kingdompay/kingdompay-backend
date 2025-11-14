# Provider Credentials Setup Guide

Step-by-step guide to get and configure payment provider credentials for KingdomPay.

---

## 1. M-Pesa (Safaricom Daraja API)

### Step 1: Register for Daraja API

1. Go to https://developer.safaricom.co.ke/
2. Click **"Get API Access"** or **"Register"**
3. Create an account (or log in if you have one)
4. Accept terms and conditions

### Step 2: Create an App

1. Navigate to **"My Apps"** in the dashboard
2. Click **"Create App"**
3. Fill in:
   - **App Name**: `KingdomPay` (or your preferred name)
   - **Short Description**: Payment processing for KingdomPay
   - **Environment**: Start with **Sandbox** for testing
4. Click **"Create"**

### Step 3: Get Sandbox Credentials

After creating the app, you'll see:

- **Consumer Key**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Consumer Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Passkey**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (for STK Push)
- **Shortcode**: `174379` (sandbox shortcode)
- **Initiator Name**: `testapi` (sandbox initiator)

**For Production** (after testing):
- You'll need to apply for production credentials
- Shortcode will be your business shortcode
- Initiator Name will be your business initiator name
- Security Credential will be generated from your certificate

### Step 4: Generate Security Credential (Production Only)

For production, you need to generate a Security Credential:

1. Download the certificate from Safaricom (provided after approval)
2. Use the certificate to encrypt your initiator password
3. Tools available:
   - Online: https://developer.safaricom.co.ke/tools
   - Python script: See `scripts/generate_mpesa_security_credential.py`

### Step 5: Configure in KingdomPay

Add to your `.env` file:

```bash
# M-Pesa (Daraja)
MPESA_CONSUMER_KEY=your_consumer_key_here
MPESA_CONSUMER_SECRET=your_consumer_secret_here
MPESA_PASSKEY=your_passkey_here
MPESA_SHORTCODE=174379
MPESA_INITIATOR_NAME=testapi
MPESA_SECURITY_CREDENTIAL=your_security_credential_here  # For production
MPESA_BASE_URL=https://sandbox.safaricom.co.ke
MPESA_CALLBACK_URL=http://localhost:5001/api/v1/webhooks/provider/MPESA
MPESA_B2C_CALLBACK_URL=http://localhost:5001/api/v1/webhooks/provider/MPESA
```

**For Production**:
```bash
MPESA_BASE_URL=https://api.safaricom.co.ke
MPESA_CALLBACK_URL=https://api.kingdompay.example/api/v1/webhooks/provider/MPESA
```

### Step 6: Test M-Pesa Integration

```bash
# Test STK Push (requires ngrok for webhooks)
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100,
    "phone": "+254708374149",
    "provider": "MPESA"
  }'
```

**Test Phone Numbers** (Sandbox):
- `254708374149` - Always succeeds
- `254712345678` - Always fails (for testing failures)

---

## 2. Airtel Money

### Step 1: Register for Airtel Money API

1. Go to https://openapi.airtel.africa/
2. Click **"Get Started"** or **"Sign Up"**
3. Create a developer account
4. Complete business verification (may take 1-2 days)

### Step 2: Create Application

1. Navigate to **"Applications"** in dashboard
2. Click **"Create Application"**
3. Fill in:
   - **Application Name**: `KingdomPay`
   - **Description**: Payment processing
   - **Environment**: **UAT** (for testing)
4. Submit for approval

### Step 3: Get Credentials

After approval, you'll receive:

- **Client ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Client Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Merchant ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (if applicable)

### Step 4: Configure in KingdomPay

Add to your `.env` file:

```bash
# Airtel Money
AIRTEL_CLIENT_ID=your_client_id_here
AIRTEL_CLIENT_SECRET=your_client_secret_here
AIRTEL_BASE_URL=https://openapiuat.airtel.africa
AIRTEL_CALLBACK_URL=http://localhost:5001/api/v1/webhooks/provider/AIRTEL
```

**For Production**:
```bash
AIRTEL_BASE_URL=https://openapi.airtel.africa
AIRTEL_CALLBACK_URL=https://api.kingdompay.example/api/v1/webhooks/provider/AIRTEL
```

### Step 5: Test Airtel Integration

```bash
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100,
    "phone": "+254712345678",
    "provider": "AIRTEL"
  }'
```

---

## 3. T-Kash

### Step 1: Contact T-Kash

1. Visit T-Kash website or contact their business development team
2. Request API access for payment processing
3. Complete business registration and verification
4. Sign API integration agreement

### Step 2: Get Credentials

After approval, you'll receive:

- **API Key**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **API Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Merchant ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 3: Configure in KingdomPay

Add to your `.env` file:

```bash
# T-Kash
TKASH_API_KEY=your_api_key_here
TKASH_API_SECRET=your_api_secret_here
TKASH_MERCHANT_ID=your_merchant_id_here
TKASH_BASE_URL=https://api.t-kash.co.ke
TKASH_CALLBACK_URL=http://localhost:5001/api/v1/webhooks/provider/TKASH
```

**For Production**:
```bash
TKASH_CALLBACK_URL=https://api.kingdompay.example/api/v1/webhooks/provider/TKASH
```

### Step 4: Test T-Kash Integration

```bash
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100,
    "phone": "+254712345678",
    "provider": "TKASH"
  }'
```

---

## 4. Webhook Configuration

### For Local Testing (ngrok)

1. **Install ngrok**:
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start ngrok**:
   ```bash
   ngrok http 5001
   ```

3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

4. **Update provider dashboards** with webhook URLs:
   - M-Pesa: `https://abc123.ngrok.io/api/v1/webhooks/provider/MPESA`
   - Airtel: `https://abc123.ngrok.io/api/v1/webhooks/provider/AIRTEL`
   - T-Kash: `https://abc123.ngrok.io/api/v1/webhooks/provider/TKASH`

5. **Update `.env`**:
   ```bash
   BASE_URL=https://abc123.ngrok.io
   MPESA_CALLBACK_URL=https://abc123.ngrok.io/api/v1/webhooks/provider/MPESA
   AIRTEL_CALLBACK_URL=https://abc123.ngrok.io/api/v1/webhooks/provider/AIRTEL
   TKASH_CALLBACK_URL=https://abc123.ngrok.io/api/v1/webhooks/provider/TKASH
   ```

### For Staging/Production

1. Use your actual domain (e.g., `https://api.kingdompay.example`)
2. Ensure HTTPS is configured
3. Update provider dashboards with production URLs
4. Update `.env` with production URLs

---

## 5. Testing Checklist

### Pre-Testing Setup

- [ ] All provider credentials added to `.env`
- [ ] Webhook URLs configured in provider dashboards
- [ ] ngrok running (for local testing)
- [ ] Backend server running (`docker-compose up` or `flask run`)
- [ ] Database migrated (`flask db upgrade`)
- [ ] System wallets initialized

### Test Scenarios

#### Test 1: M-Pesa STK Push (Success)

```bash
# 1. Get access token
TOKEN=$(curl -X POST http://localhost:5001/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254708374149"}' | jq -r '.access_token')

# 2. Verify OTP (use code from SMS/logs)
TOKEN=$(curl -X POST http://localhost:5001/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254708374149", "otp": "123456"}' | jq -r '.access_token')

# 3. Get wallet ID
WALLET_ID=$(curl -X GET http://localhost:5001/api/v1/wallets \
  -H "Authorization: Bearer $TOKEN" | jq -r '.wallets[0].id')

# 4. Initiate STK Push
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 100,
    \"phone\": \"+254708374149\",
    \"provider\": \"MPESA\",
    \"wallet_id\": $WALLET_ID
  }"

# 5. Check payment status
# Wait for webhook, then:
curl -X GET http://localhost:5001/api/v1/payments \
  -H "Authorization: Bearer $TOKEN"

# 6. Verify wallet balance updated
curl -X GET http://localhost:5001/api/v1/wallets/$WALLET_ID \
  -H "Authorization: Bearer $TOKEN"
```

#### Test 2: Webhook Reception

1. Initiate payment (see Test 1)
2. Complete payment on phone (enter PIN)
3. Check backend logs for webhook:
   ```bash
   docker-compose logs -f backend | grep webhook
   ```
4. Verify payment status changed to `SUCCESS`
5. Verify wallet balance increased

#### Test 3: Provider Failure Handling

```bash
# Use test number that always fails (M-Pesa sandbox)
curl -X POST http://localhost:5001/api/v1/topups/momo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100,
    "phone": "+254712345678",
    "provider": "MPESA"
  }'

# Verify payment status is FAILED
# Verify wallet balance unchanged
```

---

## 6. Troubleshooting

### Issue: "Invalid credentials"

**Solution**:
- Double-check Consumer Key/Secret are correct
- Ensure no extra spaces in `.env` file
- Restart backend after updating `.env`

### Issue: "Webhook not received"

**Solution**:
- Verify ngrok is running and URL is correct
- Check provider dashboard has correct webhook URL
- Verify backend is accessible from internet (ngrok tunnel)
- Check backend logs for webhook attempts

### Issue: "STK Push not appearing on phone"

**Solution**:
- Verify phone number format: `+254712345678` (with country code)
- Check M-Pesa account has sufficient balance
- Verify shortcode is correct
- Check M-Pesa account is active

### Issue: "Payment succeeded but wallet not updated"

**Solution**:
- Check webhook was received (check logs)
- Verify webhook handler processed correctly
- Check database for payment record
- Verify ledger journal was created

---

## 7. Production Checklist

Before going live:

- [ ] Production credentials obtained from all providers
- [ ] Production webhook URLs configured
- [ ] SSL certificates installed
- [ ] Webhook signature verification enabled
- [ ] Monitoring and alerts configured
- [ ] Tested with real transactions (small amounts)
- [ ] Reconciliation process verified
- [ ] Support team trained on provider issues

---

## 8. Security Notes

1. **Never commit `.env` file** to version control
2. **Use secrets management** in production (Vault, AWS KMS, etc.)
3. **Rotate credentials** regularly
4. **Monitor API usage** for suspicious activity
5. **Enable webhook signature verification** (if supported)
6. **Use HTTPS** for all webhook endpoints

---

## Quick Reference

**M-Pesa Sandbox Test Numbers**:
- Success: `254708374149`
- Failure: `254712345678`

**M-Pesa Sandbox Credentials**:
- Shortcode: `174379`
- Initiator: `testapi`
- Base URL: `https://sandbox.safaricom.co.ke`

**Webhook Testing Tools**:
- ngrok: https://ngrok.com
- webhook.site: https://webhook.site
- RequestBin: https://requestbin.com

