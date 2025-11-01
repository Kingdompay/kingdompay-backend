#!/bin/bash

# KingdomPay Production Deployment Script
# This script sets up the KingdomPay application for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="kingdompay"
APP_USER="kingdompay"
APP_DIR="/opt/kingdompay"
SERVICE_FILE="/etc/systemd/system/kingdompay.service"
NGINX_CONFIG="/etc/nginx/sites-available/kingdompay"
NGINX_ENABLED="/etc/nginx/sites-enabled/kingdompay"

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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Starting KingdomPay production deployment..."

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
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    curl \
    git \
    supervisor \
    certbot \
    python3-certbot-nginx

# Create application user
log_info "Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir $APP_DIR --create-home $APP_USER
fi

# Create application directory
log_info "Setting up application directory..."
mkdir -p $APP_DIR/{logs,uploads/kyc,ssl}
chown -R $APP_USER:$APP_USER $APP_DIR

# Clone or update application code
if [ -d "$APP_DIR/.git" ]; then
    log_info "Updating application code..."
    cd $APP_DIR
    sudo -u $APP_USER git pull
else
    log_info "Cloning application code..."
    # Replace with your actual repository URL
    sudo -u $APP_USER git clone https://github.com/your-org/kingdompay-backend.git $APP_DIR
fi

# Set up Python virtual environment
log_info "Setting up Python virtual environment..."
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt

# Set up PostgreSQL database
log_info "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE USER $APP_USER WITH PASSWORD 'your-secure-password';" || true
sudo -u postgres psql -c "CREATE DATABASE $APP_NAME OWNER $APP_USER;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $APP_NAME TO $APP_USER;" || true

# Configure Redis
log_info "Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Set up environment file
log_info "Setting up environment configuration..."
if [ ! -f "$APP_DIR/.env.production" ]; then
    cat > $APP_DIR/.env.production << EOF
# KingdomPay Production Environment
SECRET_KEY=your-super-secure-secret-key-minimum-32-characters-long
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-minimum-32-characters-long
ENCRYPTION_KEY=your-32-byte-encryption-key-here-must-be-exactly-32-bytes
DATABASE_URL=postgresql://$APP_USER:your-secure-password@localhost:5432/$APP_NAME
REDIS_URL=redis://localhost:6379/0
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
FLASK_ENV=production
APP_ENV=production
SMS_PROVIDER_API_KEY=your-sms-api-key
SMS_PROVIDER_URL=https://api.sms-provider.com
SMS_SENDER_ID=KingdomPay
EMAIL_SERVER=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@domain.com
EMAIL_PASSWORD=your-app-password
EOF
    chown $APP_USER:$APP_USER $APP_DIR/.env.production
    chmod 600 $APP_DIR/.env.production
    log_warn "Please update the environment file with your actual values: $APP_DIR/.env.production"
fi

# Run database migrations
log_info "Running database migrations..."
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/python -m flask db upgrade

# Set up systemd service
log_info "Setting up systemd service..."
cp kingdompay.service $SERVICE_FILE
systemctl daemon-reload
systemctl enable kingdompay

# Configure Nginx
log_info "Configuring Nginx..."
cat > $NGINX_CONFIG << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/auth/ {
        limit_req zone=auth burst=10 nodelay;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable Nginx site
ln -sf $NGINX_CONFIG $NGINX_ENABLED
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

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
EOF

# Set up firewall
log_info "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Start services
log_info "Starting services..."
systemctl start kingdompay
systemctl start nginx

# Check service status
log_info "Checking service status..."
systemctl status kingdompay --no-pager
systemctl status nginx --no-pager

log_info "Deployment completed successfully!"
log_warn "Don't forget to:"
log_warn "1. Update the environment file with your actual values"
log_warn "2. Configure your domain name in Nginx"
log_warn "3. Set up SSL certificates with: certbot --nginx -d your-domain.com"
log_warn "4. Test the application: curl http://your-domain.com/health"

echo ""
log_info "Useful commands:"
echo "  View logs: journalctl -u kingdompay -f"
echo "  Restart service: systemctl restart kingdompay"
echo "  Check status: systemctl status kingdompay"
echo "  View Nginx logs: tail -f /var/log/nginx/access.log"
