# KingdomPay Backend

A comprehensive Flask-based financial platform for communities, churches, and organizations to manage digital wallets, contributions, payments, and KYC compliance.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [API Endpoints](#api-endpoints)
- [Frontend Templates & Demos](#frontend-templates--demos)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)

## Overview

KingdomPay is a production-ready financial platform designed to provide secure, scalable financial services for communities. The backend API handles user authentication, digital wallet management, transaction processing, KYC compliance, and comprehensive financial operations with enterprise-grade security and reliability.

### Key Highlights

- **Secure Authentication**: OTP-based phone verification with JWT tokens
- **Digital Wallets**: Complete wallet management with transfers, deposits, and withdrawals
- **KYC Compliance**: Multi-tier verification system with document upload and risk assessment
- **Real-time Transactions**: Double-entry ledger with comprehensive audit trails
- **Frontend Demos**: Interactive HTML templates for testing and demonstration
- **Health Monitoring**: Comprehensive system health checks and performance metrics
- **Production Ready**: Docker support with cloud deployment (Render) configuration
- **Fully Tested**: Complete test suite with unit, integration, and security tests

## Features

### Authentication & Security

- **OTP-based Phone Verification**: Secure phone number authentication with SMS delivery
- **JWT Token Management**: Access and refresh token system with automatic renewal
- **Rate Limiting**: API protection against abuse and brute force attacks
- **Data Encryption**: Sensitive data encryption at rest and in transit
- **Input Validation**: Comprehensive request validation and sanitization

### Digital Wallet Management

- **Auto Wallet Creation**: Automatic wallet creation for new users
- **Balance Tracking**: Real-time balance updates with transaction history
- **Fund Transfers**: Secure wallet-to-wallet transfers with validation
- **Deposit/Withdrawal**: Add and remove funds with audit trails
- **Display Numbers**: User-friendly wallet identification system

### Transaction Processing

- **Double-Entry Ledger**: Complete transaction tracking and audit trails
- **Transaction History**: Comprehensive transaction logs with pagination
- **Real-time Updates**: Instant balance updates and transaction confirmations
- **Transaction Types**: Support for transfers, deposits, withdrawals, and more

### KYC Compliance

- **Multi-tier Verification**: Tiered KYC system (Tier 0, 1, 2)
- **Document Upload**: Support for multiple document types (ID, Passport, Utility Bills)
- **Risk Assessment**: Automated risk scoring and compliance checks
- **Transaction Limits**: Tier-based transaction limits and monitoring
- **Audit Trails**: Complete KYC process tracking and compliance logs

### Health & Monitoring

- **Health Checks**: Multiple health check endpoints for monitoring
- **System Metrics**: CPU, memory, disk, and database performance monitoring
- **Database Monitoring**: Connection health and query performance tracking
- **Redis Monitoring**: Cache performance and connectivity checks

## Architecture

### Core Components

- **Backend Framework**: Flask 2.3.3 with SQLAlchemy ORM
- **Database**: PostgreSQL 15+ (production) / SQLite (development)
- **Cache & Sessions**: Redis 7+ for caching and session management
- **Authentication**: JWT with access/refresh token system
- **Security**: Data encryption, rate limiting, input validation
- **Deployment**: Gunicorn with Docker support

### Services Architecture

- **Auth Service**: OTP verification, JWT management, user authentication
- **Wallet Service**: Wallet operations, balance management, fund transfers
- **Ledger Service**: Transaction processing, double-entry accounting
- **KYC Service**: Document verification, compliance management, risk assessment
- **SMS Service**: OTP delivery via SMS providers
- **Cache Service**: Redis-based caching and session management
- **Health Service**: System monitoring and health checks
- **Encryption Service**: Data encryption and security utilities

### Database Models

- **User**: User profiles, authentication, and account management
- **Wallet**: Digital wallets with balances and display numbers
- **Transaction**: Complete transaction records with audit trails
- **OTP Verification**: OTP codes and verification tracking
- **KYC Models**: Verification records, documents, and compliance tracking

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 15+ (or SQLite for development)
- Redis 6+ (optional for development)
- Docker (optional, for database)

### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd kingdompay-backend
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**:

   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the application**:
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:5000`

### Test the Setup

```bash
# Health check
curl http://localhost:5000/health

# Request OTP (check console for code in development)
curl -X POST http://localhost:5000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254712345678"}'
```

## Documentation

- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference with examples
- **[Setup Guide](SETUP_GUIDE.md)** - Detailed setup instructions for development and production
- **[Errors and Fixes](ERRORS_AND_FIXES.md)** - Critical issues found and recommended fixes

## API Endpoints

### Authentication & User Management

- `POST /api/v1/auth/otp/request` - Request OTP for phone verification (Rate: 5/min)
- `POST /api/v1/auth/otp/verify` - Verify OTP and get JWT tokens (Rate: 10/min)
- `POST /api/v1/auth/refresh` - Refresh access token using refresh token
- `GET /api/v1/auth/me` - Get current user information
- `PUT /api/v1/auth/profile` - Update user profile information
- `POST /api/v1/auth/logout` - Logout user and invalidate tokens

### Digital Wallet Operations

- `GET /api/v1/wallets/balance` - Get current wallet balance and details
- `GET /api/v1/wallets/transactions` - Get paginated transaction history
- `GET /api/v1/wallets/ledger` - Get wallet ledger (same as transactions)
- `POST /api/v1/wallets/transfer` - Transfer funds between wallets
- `POST /api/v1/wallets/deposit` - Add funds to wallet
- `POST /api/v1/wallets/withdraw` - Remove funds from wallet

### KYC Compliance

- `GET /api/v1/kyc/status` - Get user's KYC status and verification level
- `POST /api/v1/kyc/initiate` - Initiate KYC verification process
- `POST /api/v1/kyc/documents` - Upload KYC documents (multipart/form-data)
- `GET /api/v1/kyc/documents/<id>` - Get document information
- `POST /api/v1/kyc/verify` - Verify KYC document (admin only)
- `POST /api/v1/kyc/upgrade` - Upgrade user's KYC tier (admin only)
- `POST /api/v1/kyc/limits/check` - Check transaction limits against KYC tier
- `GET /api/v1/kyc/audit-trail` - Get KYC audit trail for user
- `GET /api/v1/kyc/documents/types` - Get supported document types
- `GET /api/v1/kyc/tiers` - Get KYC tier information and limits

### System & Health Monitoring

- `GET /health` - Basic health check endpoint
- `GET /health/detailed` - Comprehensive system health with metrics
- `GET /health/ready` - Kubernetes readiness probe endpoint
- `GET /health/live` - Kubernetes liveness probe endpoint

## Frontend Templates & Demos

KingdomPay includes interactive HTML templates for testing and demonstration purposes:

### Template Routes

- `GET /` - Main dashboard and API overview
- `GET /dashboard` - Dashboard template (same as index)
- `GET /auth-demo` - Authentication flow demonstration
- `GET /wallet-demo` - Wallet management interface

### Static HTML Files

The project also includes standalone HTML files in the `static/` directory:

- **`static/index.html`** - Main dashboard with API status and features overview
- **`static/auth.html`** - Authentication flow demonstration with OTP testing
- **`static/wallet.html`** - Wallet management interface for testing transfers
- **`static/kyc.html`** - KYC verification process demonstration
- **`static/transactions.html`** - Transaction history and ledger viewer

### Template Features

#### Dashboard Template (`/` or `/dashboard`)

- **API Status Overview**: Live status of all API endpoints
- **Feature Highlights**: Interactive cards showing system capabilities
- **Health Monitoring**: Real-time system health indicators
- **Quick Actions**: Direct links to demo pages and API testing

#### Authentication Demo (`/auth-demo`)

- **OTP Request Flow**: Test phone number verification
- **Token Management**: JWT token display and refresh testing
- **User Profile**: Profile management interface
- **Rate Limiting Demo**: Shows API rate limiting in action

#### Wallet Demo (`/wallet-demo`)

- **Balance Display**: Real-time wallet balance and details
- **Transfer Interface**: Wallet-to-wallet transfer testing
- **Transaction History**: Paginated transaction list
- **Deposit/Withdrawal**: Fund management operations

### Accessing Templates

```bash
# Start the Flask application
python run.py

# Access templates in your browser:
# Main Dashboard: http://localhost:5000/
# Authentication Demo: http://localhost:5000/auth-demo
# Wallet Demo: http://localhost:5000/wallet-demo

# Or access static files directly:
# http://localhost:5000/static/index.html
# http://localhost:5000/static/auth.html
# http://localhost:5000/static/wallet.html
# http://localhost:5000/static/kyc.html
# http://localhost:5000/static/transactions.html
```

## Implementation Status

### Fully Implemented Features

#### Authentication & Security

- OTP-based phone verification with SMS delivery
- JWT token management with refresh tokens
- Rate limiting and API protection
- Data encryption and security utilities
- Comprehensive input validation

#### Digital Wallet System

- Automatic wallet creation for new users
- Real-time balance tracking and updates
- Wallet-to-wallet fund transfers
- Deposit and withdrawal operations
- User-friendly wallet display numbers
- Complete transaction history with pagination

#### KYC Compliance System

- Multi-tier KYC verification (Tier 0, 1, 2)
- Document upload and management
- Risk assessment and scoring
- Transaction limit enforcement
- Complete audit trails and compliance tracking
- Admin verification workflows

#### System Infrastructure

- Comprehensive health monitoring
- Database and Redis connectivity checks
- System performance metrics
- Docker and cloud deployment support
- Complete test suite with coverage

## 🔧 Environment Variables

### Required

- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- `ENCRYPTION_KEY` - 32-byte encryption key

### Database

- `DATABASE_URL` - Database connection string (optional, defaults to SQLite)

### Optional

- `REDIS_URL` - Redis connection string
- `SMS_PROVIDER_API_KEY` - SMS provider API key
- `SMS_PROVIDER_URL` - SMS provider URL
- `EMAIL_SERVER` - SMTP server for emails
- `EMAIL_USERNAME` - SMTP username
- `EMAIL_PASSWORD` - SMTP password

## Deployment

### Development

```bash
# Using Flask development server
python run.py

# Using Gunicorn for production-like environment
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment

```bash
# Build the Docker image
docker build -t kingdompay-backend .

# Run with environment file
docker run -p 5000:5000 --env-file .env kingdompay-backend

# Using Docker Compose (recommended)
docker-compose up -d
```

### Render Cloud Deployment

The project includes complete Render deployment configuration:

1. **Automatic Setup**: `render.yaml` configures PostgreSQL, Redis, and web service
2. **Environment Variables**: Secure key generation and database connections
3. **Health Monitoring**: Built-in health checks and monitoring endpoints
4. **Free Tier**: 750 hours/month, 1GB PostgreSQL, 25MB Redis

See [deploy.md](deploy.md) for detailed Render deployment instructions.

### Production Considerations

- **Database**: PostgreSQL 15+ with connection pooling
- **Cache**: Redis 7+ for session management and caching
- **SSL**: Automatic SSL termination with Render
- **Monitoring**: Health checks at `/health/detailed`
- **Logging**: Structured logging with log aggregation
- **Security**: Environment-based secret management

### Future Enhancements

#### Phase 2: Community Features

- Community and organization management
- Campaign creation and management
- Contribution tracking and analytics
- Multi-user wallet sharing
- Group payment collections

#### Phase 3: Advanced Features

- Advanced reporting and analytics
- Mobile app integration
- Payment gateway integration (M-Pesa, PayPal, etc.)
- International money transfers
- Cryptocurrency support
- Advanced fraud detection
- Real-time notifications
- API webhooks for third-party integrations

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-flask

# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run specific test types
python run_tests.py --unit
python run_tests.py --integration

# Run specific test file
python run_tests.py --path tests/test_auth.py

# Run with verbose output
python run_tests.py --verbose
```

### Test Suite Coverage

The comprehensive test suite includes:

#### Unit Tests

- **Model Tests**: User, Wallet, Transaction, OTP, KYC model validation
- **Service Tests**: Auth, Wallet, Ledger, KYC, SMS service functionality
- **Utility Tests**: Encryption, validation, and helper functions

#### Integration Tests

- **API Workflows**: Complete authentication and wallet operations
- **End-to-End Scenarios**: User registration, KYC verification, fund transfers
- **Database Integration**: Transaction rollbacks, data consistency

#### Security Tests

- **Authentication**: OTP verification, JWT token handling
- **Authorization**: Protected endpoint access, permission checks
- **Rate Limiting**: OTP request limits, API abuse protection
- **Input Validation**: Malicious input handling, SQL injection prevention

#### Error Handling Tests

- **Edge Cases**: Invalid inputs, network failures, database errors
- **Business Logic**: Insufficient funds, invalid transfers, KYC limits
- **System Failures**: Service unavailability, timeout handling

### Manual Testing

```bash
# Health check
curl -X GET http://localhost:5000/health

# Test OTP flow
curl -X POST http://localhost:5000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254712345678"}'

# Test wallet operations (after authentication)
curl -X GET http://localhost:5000/api/v1/wallets/balance \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Test Coverage Reports

Test coverage reports are generated in the `htmlcov/` directory and include:

- **Line Coverage**: Code execution coverage
- **Branch Coverage**: Conditional statement coverage
- **Function Coverage**: Function call coverage
- **Class Coverage**: Class method coverage

## Monitoring

- Health check endpoint: `GET /health`
- Database connectivity monitoring
- Rate limiting metrics
- Error rate tracking

## Security

- OTP-based authentication
- JWT token security
- Rate limiting protection
- Input validation
- SQL injection prevention
- CORS configuration
- Encryption for sensitive data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:

1. Check the [Setup Guide](SETUP_GUIDE.md)
2. Review [Error Analysis](ERRORS_AND_FIXES.md)
3. Check API documentation
4. Contact the development team

## Version History

- **v1.0.0** - Initial release with basic wallet functionality
- **v1.1.0** - Added KYC compliance system and document verification
- **v1.2.0** - Enhanced security with encryption and comprehensive monitoring
- **v1.3.0** - Production-ready with Docker support and cloud deployment
- **Current** - Phase 1: Wallets + KYC + Security + Monitoring
