# KingdomPay Disaster Recovery Plan

## Overview

This document outlines the disaster recovery procedures for KingdomPay production environment.

## Recovery Time Objectives (RTO)

- **Critical Services**: 4 hours
- **Full System**: 8 hours
- **Data Recovery**: 1 hour

## Recovery Point Objectives (RPO)

- **Database**: 15 minutes
- **Application Data**: 1 hour
- **Configuration**: 24 hours

## Backup Strategy

### 1. Database Backups

```bash
# Automated daily backups
0 2 * * * /opt/kingdompay/backup.sh

# Manual backup
pg_dump -U kingdompay -h localhost kingdompay > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Application Backups

- **Code**: Git repository (primary)
- **Uploads**: Daily tar.gz backups
- **Configuration**: Version controlled
- **Logs**: Rotated and archived

### 3. Infrastructure Backups

- **Server Images**: Weekly snapshots
- **SSL Certificates**: Automated renewal
- **DNS Records**: Documented and versioned

## Disaster Scenarios & Recovery Procedures

### Scenario 1: Complete Server Failure

#### Immediate Response (0-30 minutes)

1. **Assess the situation**

   ```bash
   # Check server status
   ping your-domain.com
   ssh admin@your-domain.com
   ```

2. **Activate backup server** (if available)

   - Provision new server
   - Restore from latest snapshot

3. **Notify stakeholders**
   - Send incident notification
   - Update status page

#### Recovery Steps (30 minutes - 4 hours)

1. **Provision new server**

   ```bash
   # Run server setup
   sudo ./setup-server.sh
   ```

2. **Restore application**

   ```bash
   # Clone repository
   git clone https://github.com/your-org/kingdompay-backend.git /opt/kingdompay

   # Restore environment
   cp backup/.env.production /opt/kingdompay/

   # Install dependencies
   cd /opt/kingdompay
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```

3. **Restore database**

   ```bash
   # Create database
   sudo -u postgres createdb kingdompay

   # Restore from backup
   psql -U kingdompay -d kingdompay < latest_backup.sql
   ```

4. **Restore Redis data**

   ```bash
   # Redis persistence should auto-restore
   # If not, restore from RDB file
   cp backup/dump.rdb /var/lib/redis/
   systemctl restart redis-server
   ```

5. **Update DNS**
   - Point domain to new server IP
   - Update SSL certificates

### Scenario 2: Database Corruption

#### Immediate Response

1. **Stop application**

   ```bash
   systemctl stop kingdompay
   ```

2. **Assess corruption**
   ```bash
   # Check database integrity
   sudo -u postgres psql -d kingdompay -c "SELECT * FROM pg_stat_database;"
   ```

#### Recovery Steps

1. **Restore from backup**

   ```bash
   # Drop corrupted database
   sudo -u postgres dropdb kingdompay

   # Create new database
   sudo -u postgres createdb kingdompay

   # Restore from latest backup
   psql -U kingdompay -d kingdompay < backup_$(date +%Y%m%d).sql
   ```

2. **Verify data integrity**

   ```bash
   # Run data validation queries
   sudo -u kingdompay /opt/kingdompay/venv/bin/python -c "
   from app import create_app
   from extensions import db
   app = create_app()
   with app.app_context():
       # Add validation queries here
       print('Database validation complete')
   "
   ```

3. **Restart application**
   ```bash
   systemctl start kingdompay
   ```

### Scenario 3: Security Breach

#### Immediate Response

1. **Isolate affected systems**

   ```bash
   # Block suspicious IPs
   ufw deny from suspicious_ip

   # Stop services if necessary
   systemctl stop kingdompay
   ```

2. **Preserve evidence**
   ```bash
   # Copy logs
   cp -r /var/log/nginx /opt/kingdompay/security_incident_logs/
   cp -r /opt/kingdompay/logs /opt/kingdompay/security_incident_logs/
   ```

#### Recovery Steps

1. **Assess damage**

   - Review access logs
   - Check for data exfiltration
   - Identify compromised accounts

2. **Clean and secure**

   ```bash
   # Update all passwords
   # Rotate API keys
   # Update SSL certificates
   ```

3. **Restore from clean backup**
   - Use backup from before breach
   - Rebuild compromised components

### Scenario 4: DNS/SSL Issues

#### Immediate Response

1. **Check DNS propagation**

   ```bash
   dig your-domain.com
   nslookup your-domain.com
   ```

2. **Verify SSL certificates**
   ```bash
   openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -text -noout
   ```

#### Recovery Steps

1. **Renew SSL certificates**

   ```bash
   certbot renew --nginx
   ```

2. **Update DNS records**
   - Contact DNS provider
   - Update A/AAAA records

## Testing Procedures

### Monthly DR Tests

1. **Backup restoration test**

   ```bash
   # Test database restore
   pg_dump -U kingdompay kingdompay > test_backup.sql
   psql -U kingdompay -d kingdompay_test < test_backup.sql
   ```

2. **Application deployment test**
   - Deploy to staging environment
   - Run full test suite
   - Verify all functionality

### Quarterly Full DR Test

1. **Complete environment rebuild**
2. **End-to-end testing**
3. **Performance validation**
4. **Document lessons learned**

## Monitoring & Alerting

### Critical Alerts

- Server down
- Database unavailable
- High error rates
- Security incidents
- Backup failures

### Alert Channels

- Email notifications
- SMS alerts (for critical issues)
- Slack notifications
- PagerDuty integration

## Contact Information

### Internal Team

- **Primary On-Call**: +254-XXX-XXXX
- **Secondary On-Call**: +254-XXX-XXXX
- **Technical Lead**: tech-lead@kingdompay.com

### External Vendors

- **Hosting Provider**: support@hosting-provider.com
- **DNS Provider**: support@dns-provider.com
- **SSL Provider**: support@letsencrypt.org

## Recovery Checklist

### Pre-Recovery

- [ ] Assess the situation
- [ ] Notify stakeholders
- [ ] Gather necessary credentials
- [ ] Prepare recovery environment

### During Recovery

- [ ] Stop affected services
- [ ] Restore from backups
- [ ] Verify data integrity
- [ ] Update configurations
- [ ] Test functionality
- [ ] Monitor system health

### Post-Recovery

- [ ] Notify stakeholders of resolution
- [ ] Document incident details
- [ ] Update monitoring
- [ ] Review and improve procedures
- [ ] Schedule follow-up review

## Backup Locations

### Local Backups

- `/opt/kingdompay/backups/` - Daily backups
- `/var/lib/postgresql/` - Database files
- `/var/lib/redis/` - Redis persistence

### Remote Backups

- **AWS S3**: kingdompay-backups bucket
- **Git Repository**: Primary code backup
- **External Server**: Cross-region backup

## Recovery Scripts

### Quick Recovery Script

```bash
#!/bin/bash
# Quick recovery script for KingdomPay

set -e

echo "Starting KingdomPay recovery..."

# Restore database
echo "Restoring database..."
psql -U kingdompay -d kingdompay < /opt/kingdompay/backups/latest.sql

# Restart services
echo "Restarting services..."
systemctl restart postgresql
systemctl restart redis-server
systemctl restart kingdompay
systemctl restart nginx

# Verify services
echo "Verifying services..."
systemctl status kingdompay
curl -f http://localhost:5000/health

echo "Recovery completed successfully!"
```

This disaster recovery plan ensures KingdomPay can recover from various failure scenarios with minimal downtime and data loss.

