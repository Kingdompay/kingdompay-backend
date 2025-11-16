# M-Pesa Integration Testing Guide

This document describes how to test the M-Pesa STK Push and C2B integration.

## Test Scripts

### 1. Comprehensive Integration Test

Run the main test script that tests both C2B registration and simulation:

```bash
python3 scripts/test_mpesa_integration.py
```

This script will:

- ✅ Test C2B URL Registration
- ✅ Test C2B Payment Simulation
- 📋 Provide instructions for STK Push testing

### 2. Interactive Test Script

For interactive testing with prompts:

```bash
./scripts/run_mpesa_tests.sh
```

This provides a menu to select:

1. Test STK Push (requires manual authentication)
2. Test C2B URL Registration
3. Test C2B Payment Simulation
4. Run all tests

### 3. Individual Test Scripts

**STK Push Test:**

```bash
python3 scripts/test_stk_push.py
```

**C2B Test:**

```bash
# Register URLs
python3 scripts/test_c2b.py --register

# Simulate payment
python3 scripts/test_c2b.py --simulate
```

## Test Results

### ✅ C2B Payment Simulation - PASSED

The C2B simulation test successfully:

- Authenticates with M-Pesa API
- Simulates a C2B payment
- Returns success response

**Example Output:**

```
✅ C2B payment simulated successfully!
   Response: Accept the service request successfully.
```

### ⚠️ C2B URL Registration

C2B URL registration may require:

- Production credentials (sandbox may have limitations)
- URLs to be accessible from M-Pesa servers
- Proper SSL certificates for HTTPS URLs

**Note:** URL registration is typically done once during setup. The simulation test works without registration in sandbox mode.

## STK Push Testing

STK Push requires manual authentication. Follow these steps:

### Step 1: Request OTP

```bash
curl -X POST http://localhost:5000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254708374149"}'
```

### Step 2: Verify OTP

```bash
curl -X POST http://localhost:5000/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+254708374149",
    "otp_code": "YOUR_OTP_CODE"
  }'
```

Save the `access_token` from the response.

### Step 3: Initiate STK Push

```bash
curl -X POST http://localhost:5000/api/v1/mpesa/pay \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+254708374149",
    "amount": 100,
    "account_reference": "TEST-001",
    "transaction_desc": "Test Payment"
  }'
```

### Step 4: Complete Payment

1. Check your phone for the STK Push prompt
2. Enter your M-Pesa PIN
3. Wait for the callback to update the payment status

## Troubleshooting

### Authentication Errors

If you see "Failed to authenticate with M-Pesa API":

- Check that `MPESA_CONSUMER_KEY` and `MPESA_CONSUMER_SECRET` are set correctly
- Verify the credentials are valid for the environment (sandbox vs production)
- Check network connectivity to M-Pesa API

### 400 Errors from M-Pesa

Common causes:

- Invalid callback URL (must be HTTPS in production, accessible from internet)
- Invalid shortcode or passkey
- Invalid phone number format
- Amount below minimum or above maximum limits
- Missing or invalid account reference

**Check logs for detailed error messages:**

```bash
# If using Flask
flask run --debug

# Check application logs
tail -f logs/app.log
```

### Callback URL Issues

For local development:

1. Use ngrok or similar tool to expose local server:
   ```bash
   ngrok http 5000
   ```
2. Update `MPESA_CALLBACK_URL` in `.env` with ngrok URL
3. Restart the application

## Test Environment

### Sandbox Credentials

For testing, use M-Pesa sandbox:

- Base URL: `https://sandbox.safaricom.co.ke`
- Test phone: `+254708374149` (always accepts)
- Test phone: `+254708374150` (always rejects)

### Production

For production testing:

- Base URL: `https://api.safaricom.co.ke`
- Use real M-Pesa credentials
- Ensure callback URLs are publicly accessible with valid SSL

## Next Steps

1. ✅ C2B simulation is working
2. ⚠️ Test C2B URL registration with production credentials
3. 📱 Test STK Push with real phone number
4. 🔍 Monitor callback endpoints for webhook delivery
5. 📊 Verify payment status updates in database

## Monitoring

Check callback endpoints:

- STK Callback: `/api/v1/mpesa/callback`
- C2B Validation: `/api/v1/mpesa/validation`
- C2B Confirmation: `/api/v1/mpesa/confirmation`

Monitor webhooks:

```bash
# Watch application logs
tail -f logs/app.log | grep -i mpesa

# Check payment status
curl -X GET http://localhost:5000/api/v1/payments \
  -H "Authorization: Bearer YOUR_TOKEN"
```
