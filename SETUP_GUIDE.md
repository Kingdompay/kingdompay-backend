# KingdomPay Backend Setup Guide

## Prerequisites

Before setting up KingdomPay, ensure you have the following installed:

- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 15+** ([Download](https://www.postgresql.org/download/))
- **Redis 6+** ([Download](https://redis.io/download))
- **Docker** (optional, for database setup) ([Download](https://www.docker.com/get-started))
- **Git** ([Download](https://git-scm.com/downloads))

## Quick Start (Development)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd kingdompay-backend
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
FLASK_ENV=development

# Database Configuration (SQLite for development)
# DATABASE_URL=sqlite:///kingdompay.db

# For PostgreSQL (production):
# DATABASE_URL=postgresql://username:password@localhost:5432/kingdompay

# Redis Configuration (optional for development)
# REDIS_URL=redis://localhost:6379/0

# Encryption Key (32-byte key)
ENCRYPTION_KEY=your-32-byte-encryption-key-here

# SMS Provider (optional for development)
# SMS_PROVIDER_API_KEY=your-sms-api-key
# SMS_PROVIDER_URL=https://api.sms-provider.com
# SMS_SENDER_ID=KingdomPay

# Email Configuration (optional)
# EMAIL_SERVER=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USERNAME=your-email@gmail.com
# EMAIL_PASSWORD=your-app-password

# Rate Limiting
RATELIMIT_DEFAULT=1000 per hour
```

### 5. Database Setup

#### Option A: Using SQLite (Development - Default)

No additional setup required. The application will create a SQLite database automatically.

#### Option B: Using PostgreSQL

1. **Install PostgreSQL**:

   ```bash
   # On macOS with Homebrew:
   brew install postgresql
   brew services start postgresql

   # On Ubuntu/Debian:
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create Database**:

   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql

   # Create database and user
   CREATE DATABASE kingdompay;
   CREATE USER kingdompay_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE kingdompay TO kingdompay_user;
   \q
   ```

3. **Update Environment**:
   ```env
   DATABASE_URL=postgresql://kingdompay_user:your_password@localhost:5432/kingdompay
   ```

#### Option C: Using Docker

1. **Start PostgreSQL with Docker**:

   ```bash
   cd db
   docker-compose up -d
   ```

2. **Update Environment**:
   ```env
   DATABASE_URL=postgresql://kingdompay:password@localhost:5432/kingdompay
   ```

### 6. Initialize Database

```bash
# Initialize Flask-Migrate
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

### 7. Run the Application

```bash
# Development server
python run.py

# Or directly with Flask
python app.py
```

The API will be available at `http://localhost:5000`

## Production Setup

### 1. Environment Configuration

Create a production `.env` file:

```env
# Flask Configuration
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-secret-key
FLASK_ENV=production

# Database Configuration (Required for production)
DATABASE_URL=postgresql://username:password@host:port/database

# Redis Configuration (Required for production)
REDIS_URL=redis://username:password@host:port/database

# Encryption Key (Required for production)
ENCRYPTION_KEY=your-production-encryption-key

# SMS Provider (Required for production)
SMS_PROVIDER_API_KEY=your-sms-api-key
SMS_PROVIDER_URL=https://api.sms-provider.com
SMS_SENDER_ID=KingdomPay

# Email Configuration (Required for production)
EMAIL_SERVER=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Rate Limiting
RATELIMIT_DEFAULT=1000 per hour
RATELIMIT_STORAGE_URL=redis://username:password@host:port/database
```

### 2. Database Setup

1. **Set up PostgreSQL**:

   - Use a managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
   - Or set up your own PostgreSQL server
   - Ensure SSL is enabled for production

2. **Initialize Database**:
   ```bash
   flask db upgrade
   ```

### 3. Deploy with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. Deploy with Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:

```bash
docker build -t kingdompay-backend .
docker run -p 5000:5000 --env-file .env kingdompay-backend
```

## Environment Variables Reference

### Required Variables

| Variable         | Description            | Example                            |
| ---------------- | ---------------------- | ---------------------------------- |
| `SECRET_KEY`     | Flask secret key       | `your-secret-key-here`             |
| `JWT_SECRET_KEY` | JWT signing key        | `your-jwt-secret-key-here`         |
| `ENCRYPTION_KEY` | 32-byte encryption key | `your-32-byte-encryption-key-here` |

### Database Variables

| Variable       | Description                | Example                               |
| -------------- | -------------------------- | ------------------------------------- |
| `DATABASE_URL` | Database connection string | `postgresql://user:pass@host:port/db` |

### Optional Variables

| Variable                    | Description                    | Default                    | Example                          |
| --------------------------- | ------------------------------ | -------------------------- | -------------------------------- |
| `FLASK_ENV`                 | Flask environment              | `development`              | `production`                     |
| `REDIS_URL`                 | Redis connection string        | `redis://localhost:6379/0` | `redis://user:pass@host:port/db` |
| `JWT_ACCESS_TOKEN_EXPIRES`  | Access token expiry (seconds)  | `3600`                     | `3600`                           |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token expiry (seconds) | `2592000`                  | `2592000`                        |
| `RATELIMIT_DEFAULT`         | Default rate limit             | `1000 per hour`            | `1000 per hour`                  |
| `SMS_PROVIDER_API_KEY`      | SMS provider API key           | -                          | `your-sms-api-key`               |
| `SMS_PROVIDER_URL`          | SMS provider URL               | -                          | `https://api.sms-provider.com`   |
| `SMS_SENDER_ID`             | SMS sender ID                  | `KingdomPay`               | `KingdomPay`                     |
| `EMAIL_SERVER`              | SMTP server                    | -                          | `smtp.gmail.com`                 |
| `EMAIL_PORT`                | SMTP port                      | `587`                      | `587`                            |
| `EMAIL_USERNAME`            | SMTP username                  | -                          | `your-email@gmail.com`           |
| `EMAIL_PASSWORD`            | SMTP password                  | -                          | `your-app-password`              |

## Testing the Setup

### 1. Health Check

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "kingdompay-api",
  "version": "1.0.0"
}
```

### 2. Test OTP Flow

1. **Request OTP**:

   ```bash
   curl -X POST http://localhost:5000/api/v1/auth/otp/request \
     -H "Content-Type: application/json" \
     -d '{"phone_number": "+254712345678"}'
   ```

2. **Verify OTP** (use the code from console/logs):

   ```bash
   curl -X POST http://localhost:5000/api/v1/auth/otp/verify \
     -H "Content-Type: application/json" \
     -d '{"phone_number": "+254712345678", "otp_code": "123456", "full_name": "Test User"}'
   ```

3. **Get Wallet Balance** (use access token from step 2):
   ```bash
   curl -X GET http://localhost:5000/api/v1/wallets/balance \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Error**:

   - Check if PostgreSQL is running
   - Verify DATABASE_URL format
   - Ensure database exists and user has permissions

2. **Redis Connection Error**:

   - Check if Redis is running
   - Verify REDIS_URL format
   - Redis is optional for development

3. **Import Errors**:

   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`
   - Check Python version (3.9+)

4. **Migration Errors**:

   - Delete migration files and reinitialize
   - Check database permissions
   - Ensure database is empty before first migration

5. **OTP Not Sending**:
   - Check SMS provider configuration
   - In development, OTP codes are logged to console
   - Verify phone number format

### Logs

- **Development**: Logs are printed to console
- **Production**: Configure logging to files or external service
- **SMS**: In development, SMS content is logged to console

### Performance

- **Database**: Use connection pooling for production
- **Redis**: Configure Redis for caching and rate limiting
- **Gunicorn**: Adjust worker count based on CPU cores

## Security Considerations

1. **Environment Variables**:

   - Never commit `.env` files
   - Use strong, unique keys
   - Rotate keys regularly

2. **Database**:

   - Use SSL connections in production
   - Implement proper backup strategy
   - Use least privilege principle

3. **API Security**:

   - Enable HTTPS in production
   - Implement proper CORS policies
   - Monitor for abuse

4. **SMS Security**:
   - Use reputable SMS providers
   - Implement rate limiting
   - Log SMS activities

## Monitoring

### Health Checks

- **Application**: `GET /health`
- **Database**: Check connection status
- **Redis**: Check connection status
- **SMS Provider**: Monitor delivery rates

### Metrics

- **API Response Times**
- **Error Rates**
- **OTP Success Rates**
- **Database Performance**

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h host -U username -d kingdompay > backup.sql

# Restore
psql -h host -U username -d kingdompay < backup.sql
```

### Application Backup

- **Code**: Use version control (Git)
- **Configuration**: Backup environment files securely
- **Logs**: Implement log rotation and archival

## Support

For issues and questions:

1. Check this documentation
2. Review error logs
3. Test with minimal configuration
4. Contact development team

## Next Steps

After successful setup:

1. **Test all endpoints** using the API documentation
2. **Configure SMS provider** for production
3. **Set up monitoring** and alerting
4. **Implement backup strategy**
5. **Plan for scaling** (load balancers, multiple instances)
