# KingdomPay Production Deployment Guide

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04 LTS or higher
- **CPU**: 2+ cores
- **RAM**: 4GB+ (8GB recommended)
- **Storage**: 50GB+ SSD
- **Network**: Static IP address
- **Domain**: Registered domain name

### Required Accounts

- **SMS Provider**: Africa's Talking, Twilio, or similar
- **Email Service**: Gmail, SendGrid, or similar
- **Cloud Storage**: AWS S3 (optional)
- **Monitoring**: Prometheus + Grafana (included)

## Step-by-Step Deployment

### Step 1: Server Setup

1. **Provision Ubuntu Server**

   ```bash
   # Connect to your server
   ssh root@your-server-ip
   ```

2. **Run Server Setup Script**

   ```bash
   # Download and run setup script
   wget https://raw.githubusercontent.com/your-org/kingdompay-backend/main/setup-server.sh
   chmod +x setup-server.sh
   sudo ./setup-server.sh
   ```

3. **Verify Setup**
   ```bash
   # Check services
   systemctl status postgresql
   systemctl status redis-server
   systemctl status nginx
   ```

### Step 2: Application Deployment

1. **Upload Application Code**

   ```bash
   # Clone repository
   cd /opt/kingdompay
   sudo -u kingdompay git clone https://github.com/your-org/kingdompay-backend.git .
   ```

2. **Set Up Python Environment**

   ```bash
   cd /opt/kingdompay
   sudo -u kingdompay python3 -m venv venv
   sudo -u kingdompay venv/bin/pip install --upgrade pip
   sudo -u kingdompay venv/bin/pip install -r requirements.txt
   ```

3. **Configure Environment Variables**

   ```bash
   # Copy production environment template
   sudo -u kingdompay cp env.production.example .env.production

   # Edit with your values
   sudo -u kingdompay nano .env.production
   ```

   **Required Environment Variables:**

   ```bash
   # Generate secure keys
   SECRET_KEY=$(openssl rand -base64 32)
   JWT_SECRET_KEY=$(openssl rand -base64 32)
   ENCRYPTION_KEY=$(openssl rand -base64 32 | head -c 32)

   # Database (use generated password from setup)
   DATABASE_URL=postgresql://kingdompay:your-password@localhost:5432/kingdompay

   # Redis (use generated password from setup)
   REDIS_URL=redis://:your-redis-password@localhost:6379/0

   # SMS Provider (Africa's Talking example)
   SMS_PROVIDER=africastalking
   SMS_PROVIDER_API_KEY=your-africas-talking-api-key
   SMS_PROVIDER_URL=https://api.africastalking.com
   SMS_USERNAME=your-africas-talking-username

   # Email Configuration
   EMAIL_SERVER=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   ```

4. **Run Database Migrations**

   ```bash
   cd /opt/kingdompay
   sudo -u kingdompay venv/bin/python -m flask db upgrade
   ```

5. **Deploy Application**
   ```bash
   # Run deployment script
   sudo ./deploy.sh
   ```

### Step 3: SSL Certificate Setup

1. **Install SSL Certificate**

   ```bash
   # Replace with your domain
   sudo certbot --nginx -d api.kingdompay.com
   ```

2. **Verify SSL**

   ```bash
   # Test SSL certificate
   curl -I https://api.kingdompay.com/health
   ```

3. **Set Up Auto-Renewal**

   ```bash
   # Test renewal
   sudo certbot renew --dry-run

   # Add to crontab
   echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
   ```

### Step 4: Monitoring Setup

1. **Start Monitoring Services**

   ```bash
   # Start Prometheus and Grafana
   docker-compose -f docker-compose.production.yml up -d prometheus grafana
   ```

2. **Configure Grafana**

   - Access Grafana: `http://your-server-ip:3000`
   - Default login: `admin` / `admin`
   - Import dashboard from `monitoring/grafana-dashboard.json`

3. **Set Up Alerting**

   ```bash
   # Copy alert rules
   sudo cp monitoring/alerts.yml /etc/prometheus/alerts.yml

   # Update Prometheus config
   sudo nano /etc/prometheus/prometheus.yml
   ```

### Step 5: Backup Configuration

1. **Test Backup Script**

   ```bash
   # Run backup manually
   sudo -u kingdompay /opt/kingdompay/backup.sh

   # Verify backup
   ls -la /opt/kingdompay/backups/
   ```

2. **Set Up Remote Backups** (Optional)

   ```bash
   # Install AWS CLI
   sudo apt install awscli

   # Configure AWS credentials
   sudo -u kingdompay aws configure

   # Update backup script to include S3 upload
   ```

### Step 6: Security Hardening

1. **Configure Firewall**

   ```bash
   # Restrict database and Redis access
   sudo ufw deny 5432
   sudo ufw deny 6379

   # Allow only necessary ports
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. **Set Up Fail2ban**

   ```bash
   # Configure fail2ban
   sudo nano /etc/fail2ban/jail.local

   # Restart fail2ban
   sudo systemctl restart fail2ban
   ```

3. **Update System**
   ```bash
   # Regular security updates
   sudo apt update && sudo apt upgrade -y
   ```

## Verification & Testing

### 1. Health Checks

```bash
# Application health
curl https://api.kingdompay.com/health

# Detailed health
curl https://api.kingdompay.com/health/detailed

# Metrics
curl https://api.kingdompay.com/metrics
```

### 2. API Testing

```bash
# Test authentication
curl -X POST https://api.kingdompay.com/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254700000000"}'

# Test wallet creation
curl -X POST https://api.kingdompay.com/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+254700000000", "otp_code": "123456", "full_name": "Test User"}'
```

### 3. Performance Testing

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Test performance
ab -n 1000 -c 10 https://api.kingdompay.com/health
```

## Maintenance Procedures

### Daily Tasks

- [ ] Check system health
- [ ] Review logs for errors
- [ ] Monitor resource usage
- [ ] Verify backups

### Weekly Tasks

- [ ] Update system packages
- [ ] Review security logs
- [ ] Test backup restoration
- [ ] Performance analysis

### Monthly Tasks

- [ ] Security audit
- [ ] Disaster recovery test
- [ ] Capacity planning review
- [ ] Documentation updates

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check logs
journalctl -u kingdompay -f

# Check environment
sudo -u kingdompay cat /opt/kingdompay/.env.production

# Test database connection
sudo -u kingdompay /opt/kingdompay/venv/bin/python -c "
from app import create_app
from extensions import db
app = create_app()
app.app_context().push()
print('DB OK' if db.engine.execute('SELECT 1') else 'DB ERROR')
"
```

#### 2. Database Connection Issues

```bash
# Check PostgreSQL status
systemctl status postgresql

# Check database exists
sudo -u postgres psql -l

# Test connection
psql -U kingdompay -h localhost -d kingdompay
```

#### 3. Redis Connection Issues

```bash
# Check Redis status
systemctl status redis-server

# Test Redis connection
redis-cli ping

# Check Redis logs
journalctl -u redis-server -f
```

#### 4. SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --nginx

# Test SSL
openssl s_client -connect api.kingdompay.com:443
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for better performance
CREATE INDEX CONCURRENTLY idx_transactions_created_at ON transactions(created_at);
CREATE INDEX CONCURRENTLY idx_users_phone ON users(phone_number);
CREATE INDEX CONCURRENTLY idx_wallets_user_id ON wallets(user_id);
```

### 2. Redis Optimization

```bash
# Configure Redis for production
sudo nano /etc/redis/redis.conf

# Set memory policy
maxmemory-policy allkeys-lru

# Enable persistence
save 900 1
save 300 10
save 60 10000
```

### 3. Nginx Optimization

```nginx
# Add to nginx.conf
worker_processes auto;
worker_connections 1024;

# Enable gzip
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_comp_level 6;
```

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use nginx or cloud load balancer
2. **Multiple App Servers**: Deploy multiple instances
3. **Database Replicas**: Set up read replicas
4. **Redis Cluster**: Use Redis Cluster for high availability

### Vertical Scaling

1. **Increase Server Resources**: More CPU, RAM, storage
2. **Optimize Application**: Code profiling and optimization
3. **Database Tuning**: Query optimization and indexing
4. **Caching Strategy**: Implement application-level caching

## Security Checklist

- [ ] SSL certificates installed and auto-renewing
- [ ] Firewall configured and enabled
- [ ] Fail2ban configured and active
- [ ] Strong passwords and API keys
- [ ] Regular security updates
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Access logs monitored
- [ ] Security headers configured
- [ ] Rate limiting enabled

## Support & Maintenance

### Monitoring Dashboards

- **Grafana**: http://your-server-ip:3000
- **Prometheus**: http://your-server-ip:9090
- **Application Logs**: `/opt/kingdompay/logs/`

### Contact Information

- **Technical Support**: support@kingdompay.com
- **Emergency**: +254-XXX-XXXX
- **Documentation**: https://docs.kingdompay.com

This deployment guide ensures a robust, secure, and scalable production environment for KingdomPay.

