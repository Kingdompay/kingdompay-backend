#!/bin/bash

# KingdomPay Production Server Setup Script
# Run this script on a fresh Ubuntu 20.04+ server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN_NAME=""
EMAIL=""
APP_NAME="kingdompay"
APP_USER="kingdompay"
APP_DIR="/opt/kingdompay"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Get domain and email from user
if [ -z "$DOMAIN_NAME" ]; then
    read -p "Enter your domain name (e.g., api.kingdompay.com): " DOMAIN_NAME
fi

if [ -z "$EMAIL" ]; then
    read -p "Enter your email address for SSL certificates: " EMAIL
fi

log_step "Setting up KingdomPay production server for domain: $DOMAIN_NAME"

# Update system packages
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required system packages
log_info "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    curl \
    git \
    supervisor \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    htop \
    vim \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Configure PostgreSQL
log_info "Configuring PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER $APP_USER WITH PASSWORD '$(openssl rand -base64 32)';" || true
sudo -u postgres psql -c "CREATE DATABASE $APP_NAME OWNER $APP_USER;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $APP_NAME TO $APP_USER;" || true

# Configure Redis
log_info "Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Configure Redis security
sed -i 's/# requirepass foobared/requirepass $(openssl rand -base64 32)/' /etc/redis/redis.conf
systemctl restart redis-server

# Create application user
log_info "Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir $APP_DIR --create-home $APP_USER
fi

# Create application directory structure
log_info "Setting up application directory..."
mkdir -p $APP_DIR/{logs,uploads/kyc,ssl,backups}
chown -R $APP_USER:$APP_USER $APP_DIR

# Configure firewall
log_info "Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5432/tcp  # PostgreSQL (restrict this later)
ufw allow 6379/tcp  # Redis (restrict this later)

# Configure fail2ban
log_info "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Set up log rotation
log_info "Setting up log rotation..."
cat > /etc/logrotate.d/kingdompay << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload kingdompay
    endscript
}

/var/log/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data adm
    postrotate
        systemctl reload nginx
    endscript
}
EOF

# Create backup script
log_info "Setting up backup script..."
cat > $APP_DIR/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/kingdompay/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="kingdompay"
DB_USER="kingdompay"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U $DB_USER -h localhost $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /opt/kingdompay/uploads /opt/kingdompay/.env.production

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x $APP_DIR/backup.sh
chown $APP_USER:$APP_USER $APP_DIR/backup.sh

# Set up cron job for backups
echo "0 2 * * * $APP_USER $APP_DIR/backup.sh" | crontab -u $APP_USER -

# Create monitoring script
log_info "Setting up monitoring script..."
cat > $APP_DIR/monitor.sh << 'EOF'
#!/bin/bash
LOG_FILE="/opt/kingdompay/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check if application is running
if ! systemctl is-active --quiet kingdompay; then
    echo "$DATE - ERROR: KingdomPay service is not running" >> $LOG_FILE
    systemctl start kingdompay
fi

# Check database connection
if ! sudo -u kingdompay /opt/kingdompay/venv/bin/python -c "from app import create_app; from extensions import db; app = create_app(); app.app_context().push(); db.engine.execute('SELECT 1')" 2>/dev/null; then
    echo "$DATE - ERROR: Database connection failed" >> $LOG_FILE
fi

# Check Redis connection
if ! redis-cli ping > /dev/null 2>&1; then
    echo "$DATE - ERROR: Redis connection failed" >> $LOG_FILE
fi

# Check disk space
DISK_USAGE=$(df /opt/kingdompay | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$DATE - WARNING: Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 90 ]; then
    echo "$DATE - WARNING: Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
fi
EOF

chmod +x $APP_DIR/monitor.sh
chown $APP_USER:$APP_USER $APP_DIR/monitor.sh

# Set up monitoring cron job
echo "*/5 * * * * $APP_USER $APP_DIR/monitor.sh" | crontab -u $APP_USER -

log_info "Production server setup completed!"
log_warn "Next steps:"
log_warn "1. Upload your application code to $APP_DIR"
log_warn "2. Configure environment variables in $APP_DIR/.env.production"
log_warn "3. Run the deployment script: sudo ./deploy.sh"
log_warn "4. Set up SSL certificates: sudo certbot --nginx -d $DOMAIN_NAME"
log_warn "5. Configure monitoring and alerts"

echo ""
log_info "Generated passwords:"
echo "Database password: Check PostgreSQL logs"
echo "Redis password: Check /etc/redis/redis.conf"
echo ""
log_info "Server is ready for KingdomPay deployment!"

