# KingdomPay Backend

A Flask-based financial platform for communities, churches, and organizations to manage digital wallets, contributions, and payments.

## Phase 1: Wallets + Communities + Giving

This implementation focuses on the core functionality:

- User authentication with OTP
- Digital wallet management
- Community creation and management
- Campaign and contribution tracking
- Double-entry ledger system

## Architecture

- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL
- **Cache**: Redis
- **Authentication**: JWT with refresh tokens
- **Security**: Encryption, rate limiting, input validation

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 15+
- Redis 6+
- Docker (optional, for database)

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd kingdompay-backend
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp env.example .env
# Edit .env with your configuration
```

5. Start the database (using Docker):

```bash
cd db
docker-compose up -d
```

6. Initialize the database:

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

7. Run the application:

```bash
python run.py
```

The API will be available at `http://localhost:5000`

## Environment Variables

Key environment variables (see `env.example` for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `ENCRYPTION_KEY`: 32-byte key for data encryption

## API Documentation

The API follows RESTful conventions with versioning:

- Base URL: `/api/v1`
- Authentication: Bearer token in Authorization header
- Content-Type: `application/json`

### Key Endpoints

- `POST /api/v1/auth/otp/request` - Request OTP
- `POST /api/v1/auth/otp/verify` - Verify OTP and get tokens
- `POST /api/v1/communities` - Create community
- `POST /api/v1/transfers` - Transfer between wallets
- `GET /api/v1/wallets/{id}/balance` - Get wallet balance

## Security Features

- JWT-based authentication with refresh tokens
- Rate limiting on all endpoints
- Input validation and sanitization
- Data encryption for sensitive information
- Idempotency keys for financial operations
- Double-entry ledger for all money movements

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

### Code Style

The project uses:

- Black for code formatting
- Flake8 for linting
- Type hints for better code documentation

## License

[Add your license here]
