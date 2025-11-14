# KingdomPay Production Deployment Checklist

## Pre-Deployment Checklist

### Server Preparation

- [ ] Ubuntu 20.04+ server provisioned
- [ ] Static IP address assigned
- [ ] Domain name registered and configured
- [ ] DNS records pointing to server IP
- [ ] SSH access configured with key-based authentication

### Required Services

- [ ] SMS provider account (Africa's Talking/Twilio)
- [ ] Email service account (Gmail/SendGrid)
- [ ] Cloud storage account (AWS S3) - Optional
- [ ] Monitoring account (Prometheus/Grafana) - Included

## Deployment Steps

### 1. Server Setup

- [ ] Run `sudo ./setup-server.sh`
- [ ] Verify PostgreSQL is running
- [ ] Verify Redis is running
- [ ] Verify Nginx is running
- [ ] Check firewall configuration

### 2. Application Deployment

- [ ] Clone repository to `/opt/kingdompay`
- [ ] Set up Python virtual environment
- [ ] Install dependencies from `requirements.txt`
- [ ] Copy `env.production.example` to `.env.production`
- [ ] Configure all required environment variables
- [ ] Run database migrations: `flask db upgrade`
- [ ] Run `sudo ./deploy.sh`

### 3. SSL Configuration

- [ ] Install SSL certificate: `sudo certbot --nginx -d your-domain.com`
- [ ] Verify SSL certificate is working
- [ ] Test HTTPS endpoints
- [ ] Set up auto-renewal

### 4. Monitoring Setup

- [ ] Start Prometheus and Grafana services
- [ ] Import Grafana dashboard
- [ ] Configure alerting rules
- [ ] Test monitoring endpoints

### 5. Security Configuration

- [ ] Configure firewall rules
- [ ] Set up fail2ban
- [ ] Update system packages
- [ ] Configure security headers
- [ ] Test rate limiting

## Environment Variables Checklist

### Required Variables

- [ ] `SECRET_KEY` - 32+ character random string
- [ ] `JWT_SECRET_KEY` - 32+ character random string
- [ ] `ENCRYPTION_KEY` - Exactly 32 bytes
- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `REDIS_URL` - Redis connection string
- [ ] `RATELIMIT_STORAGE_URL` - Redis for rate limiting
- [ ] `SMS_PROVIDER_API_KEY` - SMS service API key
- [ ] `SMS_PROVIDER_URL` - SMS service endpoint
- [ ] `EMAIL_USERNAME` - Email service username
- [ ] `EMAIL_PASSWORD` - Email service password

### Optional Variables

- [ ] `AWS_ACCESS_KEY_ID` - For file uploads
- [ ] `AWS_SECRET_ACCESS_KEY` - For file uploads
- [ ] `S3_BUCKET` - For file storage
- [ ] `PROMETHEUS_PORT` - Monitoring port
- [ ] `LOG_LEVEL` - Logging level

## Testing Checklist

### Health Checks

- [ ] `GET /health` returns 200
- [ ] `GET /health/detailed` returns system metrics
- [ ] `GET /health/ready` returns readiness status
- [ ] `GET /health/live` returns liveness status
- [ ] `GET /metrics` returns Prometheus metrics

### API Endpoints

- [ ] `POST /api/v1/auth/send-otp` works
- [ ] `POST /api/v1/auth/verify-otp` works
- [ ] `GET /api/v1/wallet/balance` requires authentication
- [ ] `POST /api/v1/wallet/transfer` works
- [ ] Error responses have proper format

### Security Tests

- [ ] Rate limiting works on auth endpoints
- [ ] CSRF protection works on state-changing operations
- [ ] Security headers are present
- [ ] SSL certificate is valid
- [ ] Input validation works

### Performance Tests

- [ ] Application responds within 2 seconds
- [ ] Database queries are optimized
- [ ] Redis caching works
- [ ] Static files are served efficiently
- [ ] Load testing passes

## Backup & Recovery

### Backup Configuration

- [ ] Database backup script configured
- [ ] Application files backup configured
- [ ] Backup rotation policy set
- [ ] Remote backup configured (optional)
- [ ] Backup restoration tested

### Monitoring & Alerting

- [ ] Prometheus metrics collection
- [ ] Grafana dashboards configured
- [ ] Alert rules defined
- [ ] Notification channels configured
- [ ] Log aggregation set up

## Post-Deployment

### Documentation

- [ ] Update deployment documentation
- [ ] Document any custom configurations
- [ ] Create runbook for common issues
- [ ] Update contact information
- [ ] Document backup procedures

### Team Handover

- [ ] Provide access credentials
- [ ] Train team on monitoring
- [ ] Document maintenance procedures
- [ ] Set up on-call rotation
- [ ] Create incident response plan

## Maintenance Schedule

### Daily

- [ ] Check system health
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Verify backups

### Weekly

- [ ] Update system packages
- [ ] Review security logs
- [ ] Test backup restoration
- [ ] Performance analysis

### Monthly

- [ ] Security audit
- [ ] Disaster recovery test
- [ ] Capacity planning
- [ ] Documentation review

## Emergency Contacts

### Internal Team

- **Primary On-Call**: +254-XXX-XXXX
- **Secondary On-Call**: +254-XXX-XXXX
- **Technical Lead**: tech-lead@kingdompay.com

### External Vendors

- **Hosting Provider**: support@hosting-provider.com
- **DNS Provider**: support@dns-provider.com
- **SMS Provider**: support@sms-provider.com
- **Email Provider**: support@email-provider.com

## Quick Commands

### Service Management

```bash
# Check service status
systemctl status kingdompay
systemctl status postgresql
systemctl status redis-server
systemctl status nginx

# Restart services
systemctl restart kingdompay
systemctl restart nginx

# View logs
journalctl -u kingdompay -f
tail -f /var/log/nginx/access.log
```

### Database Operations

```bash
# Connect to database
psql -U kingdompay -d kingdompay

# Run migrations
cd /opt/kingdompay && python -m flask db upgrade

# Create backup
pg_dump -U kingdompay kingdompay > backup.sql
```

### Monitoring

```bash
# Check application health
curl https://api.kingdompay.com/health

# Check metrics
curl https://api.kingdompay.com/metrics

# View Grafana
open http://your-server-ip:3000
```

This checklist ensures a complete and successful production deployment of KingdomPay.

