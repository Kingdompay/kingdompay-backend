# Quick Start Guide - Running KingdomPay Backend

## What Was Fixed

The Flask app was not running because:

1. **Template folder was misconfigured** - Flask was looking for templates in a `templates/` folder, but the HTML files are in the `static/` folder
2. **Static folder configuration** - Updated to serve files from the `static/` directory

## How to Run the App

### Option 1: Using run.py (Recommended)

```bash
cd kingdompay-backend
python3 run.py
```

The app will start on port **5000** by default (or use the `PORT` environment variable).

### Option 2: Using app.py directly

```bash
cd kingdompay-backend
python3 app.py
```

The app will start on port **5040** (as specified in app.py).

### Option 3: Using Flask CLI

```bash
cd kingdompay-backend
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

## Access Points

Once running, you can access:

### Backend API

- **Health Check**: http://localhost:5000/health
- **API Base**: http://localhost:5000/api/v1
- **Dashboard**: http://localhost:5000/

### Frontend Templates

- **Main Dashboard**: http://localhost:5000/dashboard
- **Auth Demo**: http://localhost:5000/auth-demo
- **Wallet Demo**: http://localhost:5000/wallet-demo

### Static Files (Direct Access)

- **Index**: http://localhost:5000/index.html
- **Auth**: http://localhost:5000/auth.html
- **Wallet**: http://localhost:5000/wallet.html
- **Transactions**: http://localhost:5000/transactions.html
- **KYC**: http://localhost:5000/kyc.html

## API Endpoints

### Authentication

- `POST /api/v1/auth/otp/request` - Request OTP code
- `POST /api/v1/auth/otp/verify` - Verify OTP and login
- `GET /api/v1/auth/me` - Get current user info

### Wallet

- `GET /api/v1/wallets/balance` - Get wallet balance
- `GET /api/v1/wallets/transactions` - Get transaction history
- `POST /api/v1/wallets/transfer` - Transfer funds

### KYC

- `GET /api/v1/kyc/status` - Get KYC verification status
- `POST /api/v1/kyc/documents` - Upload KYC documents

## Environment Setup

Ensure you have a `.env` file with the following variables:

```env
# Required Secrets
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-encryption-key

# Database (Optional - defaults to SQLite)
DATABASE_URL=sqlite:///kingdompay.db

# Redis (Optional)
REDIS_URL=redis://localhost:6379

# Port
PORT=5000
```

## Troubleshooting

### Issue: Port already in use

**Solution**: Change the port

```bash
PORT=5001 python3 run.py
```

### Issue: Module not found errors

**Solution**: Install dependencies

```bash
pip3 install -r requirements.txt
```

### Issue: Database errors

**Solution**: Initialize the database

```bash
python3 run.py
# In another terminal:
flask db upgrade
```

### Issue: Redis connection error

**Solution**: The app will work without Redis, but rate limiting will be less effective. Either:

1. Install and start Redis: `brew install redis && redis-server`
2. Or ignore the warning - it will fallback to in-memory storage

### Issue: Templates not found

**Solution**: This is now fixed! The app is configured to look in the `static/` folder for templates.

## Development vs Production

### Development

```bash
python3 run.py
```

- Uses SQLite database
- Debug mode enabled
- No caching
- Port: 5000

### Production

Use `gunicorn`:

```bash
pip3 install gunicorn
gunicorn app:app -b 0.0.0.0:5000
```

- Requires PostgreSQL (set DATABASE_URL)
- Debug mode disabled
- Redis caching enabled
- Uses production config

## Testing the Integration

1. **Start the backend**:

   ```bash
   python3 run.py
   ```

2. **Open browser to**: http://localhost:5000/dashboard

3. **Test Authentication**:

   - Go to http://localhost:5000/auth-demo
   - Enter phone number
   - Check terminal for OTP code
   - Enter OTP and complete registration

4. **Test Wallet**:
   - After authentication, go to http://localhost:5000/wallet-demo
   - Should see your balance
   - Can transfer funds (if you have another user)

## Next Steps

1. ✅ App is now running correctly
2. ✅ Templates are accessible
3. ✅ API is connected to frontend
4. Next: Test the full flow (auth → wallet → transactions → KYC)

## Support

If you encounter issues:

1. Check terminal output for error messages
2. Verify .env file has all required variables
3. Check port is not in use: `lsof -i :5000`
4. Review logs for detailed error information
