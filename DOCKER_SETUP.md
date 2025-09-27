# KingdomPay Docker Setup Guide

This guide explains how to set up and run KingdomPay using Docker for development and production environments.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for containers
- 10GB free disk space

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd kingdompay-backend

# Copy environment file
cp env.docker.example .env

# Edit environment variables (optional)
nano .env
```

### 2. Start Services

```bash
# Start all services (database, redis, backend)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check service status
docker-compose ps
```

### 3. Access Services

- **API**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **Detailed Health**: http://localhost:5000/health/detailed
- **PgAdmin**: http://localhost:5050 (admin@kingdompay.com / admin123)
- **Redis Commander**: http://localhost:8081

## Service Architecture

### Core Services

1. **Backend Application** (`backend`)

   - Flask application with Gunicorn
   - 4 worker processes
   - Health checks enabled
   - Auto-restart on failure

2. **PostgreSQL Database** (`postgres`)

   - PostgreSQL 15
   - Persistent data storage
   - Health checks enabled
   - Port: 5433 (external), 5432 (internal)

3. **Redis Cache** (`redis`)
   - Redis 7 Alpine
   - Session storage and caching
   - Persistent data with AOF
   - Port: 6379

### Optional Tools (Profile: tools)

4. **PgAdmin** (`pgadmin`)

   - Database management interface
   - Access: http://localhost:5050
   - Credentials: admin@kingdompay.com / admin123

5. **Redis Commander** (`redis-commander`)
   - Redis management interface
   - Access: http://localhost:8081

## Environment Configuration

### Required Environment Variables

```bash
# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
ENCRYPTION_KEY=your-encryption-key-here-change-in-production

# Application
APP_ENV=production
LOG_LEVEL=INFO
```

### Database Configuration

```bash
# Database (automatically configured in Docker)
DATABASE_URL=postgresql://admin:admin123@postgres:5432/kingdompay
```

### Redis Configuration

```bash
# Redis (automatically configured in Docker)
REDIS_URL=redis://redis:6379/0
RATELIMIT_STORAGE_URL=redis://redis:6379/1
```

## Development Workflow

### 1. Start Development Environment

```bash
# Start only database and redis
docker-compose up -d postgres redis

# Run Flask app locally for development
python app.py
```

### 2. Database Management

```bash
# Access database directly
docker-compose exec postgres psql -U admin -d kingdompay

# Run migrations
docker-compose exec backend flask db upgrade

# Create new migration
docker-compose exec backend flask db migrate -m "description"
```

### 3. Redis Management

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Monitor Redis commands
docker-compose exec redis redis-cli monitor
```

## Production Deployment

### 1. Security Configuration

```bash
# Generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file with production values
SECRET_KEY=<generated-secret-key>
JWT_SECRET_KEY=<generated-jwt-key>
ENCRYPTION_KEY=<generated-encryption-key>
```

### 2. Production Environment

```bash
# Set production environment
export APP_ENV=production

# Start production services
docker-compose up -d

# Verify health
curl http://localhost:5000/health/detailed
```

### 3. Monitoring and Logs

```bash
# View application logs
docker-compose logs -f backend

# View all service logs
docker-compose logs -f

# Check resource usage
docker stats
```

## Database Setup

### 1. Initial Database Setup

```bash
# Run database initialization scripts
docker-compose exec postgres psql -U admin -d kingdompay -f /docker-entrypoint-initdb.d/users\ table.sql
docker-compose exec postgres psql -U admin -d kingdompay -f /docker-entrypoint-initdb.d/wallettable.sql
docker-compose exec postgres psql -U admin -d kingdompay -f /docker-entrypoint-initdb.d/transactiontable.sql
docker-compose exec postgres psql -U admin -d kingdompay -f /docker-entrypoint-initdb.d/otp_table.sql
docker-compose exec postgres psql -U admin -d kingdompay -f /docker-entrypoint-initdb.d/kyc_tables.sql
```

### 2. Run Migrations

```bash
# Initialize migrations (first time only)
docker-compose exec backend flask db init

# Run migrations
docker-compose exec backend flask db upgrade
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**

   ```bash
   # Check port usage
   netstat -tulpn | grep :5000

   # Change ports in docker-compose.yml if needed
   ```

2. **Permission Issues**

   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

3. **Database Connection Issues**

   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U admin -d kingdompay

   # View database logs
   docker-compose logs postgres
   ```

4. **Redis Connection Issues**

   ```bash
   # Check Redis health
   docker-compose exec redis redis-cli ping

   # View Redis logs
   docker-compose logs redis
   ```

### Health Checks

```bash
# Basic health check
curl http://localhost:5000/health

# Detailed system health
curl http://localhost:5000/health/detailed

# Readiness check (for Kubernetes)
curl http://localhost:5000/health/ready

# Liveness check (for Kubernetes)
curl http://localhost:5000/health/live
```

### Logs and Debugging

```bash
# View specific service logs
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# View logs with timestamps
docker-compose logs -f -t backend

# Follow logs in real-time
docker-compose logs -f --tail=100 backend
```

## Scaling and Performance

### 1. Horizontal Scaling

```bash
# Scale backend service
docker-compose up -d --scale backend=3

# Check load balancing
docker-compose ps
```

### 2. Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "0.5"
        reservations:
          memory: 512M
          cpus: "0.25"
```

### 3. Performance Monitoring

```bash
# Monitor resource usage
docker stats

# Check container health
docker-compose ps
```

## Backup and Recovery

### 1. Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U admin kingdompay > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U admin kingdompay < backup.sql
```

### 2. Redis Backup

```bash
# Redis automatically persists data with AOF
# Manual backup
docker-compose exec redis redis-cli BGSAVE
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: This deletes all data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker system prune -a
```

## Security Considerations

1. **Change default passwords** in production
2. **Use secrets management** for sensitive data
3. **Enable SSL/TLS** for external access
4. **Regular security updates** for base images
5. **Network isolation** for production deployments
6. **Backup encryption** for sensitive data

## Support

For issues and questions:

- Check the logs: `docker-compose logs -f`
- Verify health: `curl http://localhost:5000/health/detailed`
- Review configuration in `.env` file
- Check Docker and Docker Compose versions
