# Ngrok Setup for M-Pesa Callback Testing

This guide explains how to set up ngrok for local M-Pesa callback testing.

## Why Ngrok?

M-Pesa's Daraja API requires a publicly accessible callback URL to send webhook notifications. When developing locally, your server runs on `localhost`, which M-Pesa cannot reach. Ngrok creates a secure tunnel that exposes your local server to the internet.

## Prerequisites

1. **Install ngrok**:
   ```bash
   # macOS
   brew install ngrok
   
   # Linux
   # Download from https://ngrok.com/download
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   tar -xzf ngrok-v3-stable-linux-amd64.tgz
   sudo mv ngrok /usr/local/bin/
   
   # Windows
   # Download from https://ngrok.com/download
   ```

2. **Sign up for ngrok** (free):
   - Go to https://dashboard.ngrok.com/signup
   - Create a free account
   - Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

3. **Authenticate ngrok**:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

## Quick Setup

### Option 1: Automatic Setup (Recommended)

Run the setup script:

```bash
cd kingdompay-backend
./scripts/setup_ngrok_callback.sh
```

This script will:
- ✅ Check if ngrok is installed
- ✅ Start ngrok tunnel on port 5001
- ✅ Extract the public URL
- ✅ Update `MPESA_CALLBACK_URL` in your `.env` file
- ✅ Update `MPESA_B2C_CALLBACK_URL` if present

Then restart your backend:

```bash
docker-compose restart backend
```

### Option 2: Start Everything Together

Use the combined script:

```bash
cd kingdompay-backend
./scripts/start_with_ngrok.sh
```

This will:
- ✅ Setup ngrok and update callback URLs
- ✅ Start backend services

### Option 3: Manual Setup

1. **Start ngrok**:
   ```bash
   ngrok http 5001
   ```

2. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

3. **Update `.env` file**:
   ```bash
   MPESA_CALLBACK_URL=https://abc123.ngrok.io/api/v1/webhooks/provider/MPESA
   MPESA_B2C_CALLBACK_URL=https://abc123.ngrok.io/api/v1/webhooks/provider/MPESA
   ```

4. **Restart backend**:
   ```bash
   docker-compose restart backend
   ```

## Verification

1. **Check ngrok is running**:
   ```bash
   curl http://localhost:4040/api/tunnels
   ```

2. **Verify callback URL in .env**:
   ```bash
   grep MPESA_CALLBACK_URL .env
   ```

3. **Test the callback endpoint**:
   ```bash
   # Get your ngrok URL
   NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)
   
   # Test the webhook endpoint
   curl -X POST "${NGROK_URL}/api/v1/webhooks/provider/MPESA" \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

## Ngrok Dashboard

Access the ngrok web interface:
- **URL**: http://localhost:4040
- View all requests, inspect payloads, and replay requests

## Important Notes

### Free vs Paid ngrok

- **Free tier**: URL changes every time you restart ngrok
- **Paid tier**: Static domain (recommended for production testing)

### Keeping ngrok Running

- Keep the terminal with ngrok open, or
- Run ngrok in background: `ngrok http 5001 > /dev/null 2>&1 &`
- Use a process manager like `screen` or `tmux`

### Production

For production, you don't need ngrok. Use:
- Your actual domain: `https://api.kingdompay.com/api/v1/webhooks/provider/MPESA`
- Ensure HTTPS is enabled
- Configure firewall rules appropriately

## Troubleshooting

### Ngrok not starting

```bash
# Check if ngrok is authenticated
ngrok config check

# Re-authenticate if needed
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### Port already in use

```bash
# Kill existing ngrok process
pkill ngrok

# Or kill process on port 4040
lsof -ti:4040 | xargs kill -9
```

### Callback URL not updating

```bash
# Manually check and update
grep MPESA_CALLBACK_URL .env

# Edit manually if needed
nano .env
```

### M-Pesa still returns 400

1. Verify ngrok URL is accessible:
   ```bash
   curl https://your-ngrok-url.ngrok.io/health
   ```

2. Check callback URL format:
   - Must start with `https://`
   - Must end with `/api/v1/webhooks/provider/MPESA`
   - No trailing slash

3. Verify credentials:
   ```bash
   grep MPESA_PASSKEY .env
   grep MPESA_SHORTCODE .env
   ```

## Scripts Reference

- `scripts/setup_ngrok_callback.sh` - Setup ngrok and update .env
- `scripts/start_with_ngrok.sh` - Setup ngrok and start services
- `test_real_stk_push.sh` - Test M-Pesa STK Push end-to-end

## Next Steps

After setting up ngrok:

1. ✅ Verify callback URL is set
2. ✅ Restart backend services
3. ✅ Run STK Push test: `./test_real_stk_push.sh`
4. ✅ Check ngrok dashboard for incoming webhooks

