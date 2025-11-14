#!/bin/bash
# KingdomPay Deployment Script
# Usage: ./scripts/deploy.sh [environment] [action]
# Example: ./scripts/deploy.sh staging deploy

set -e

ENV=${1:-staging}
ACTION=${2:-deploy}

echo "🚀 KingdomPay Deployment - Environment: $ENV, Action: $ACTION"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: docker is required${NC}" >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Error: docker-compose is required${NC}" >&2; exit 1; }

# Load environment-specific config
ENV_FILE=".env.$ENV"
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${YELLOW}Warning: $ENV_FILE not found. Using defaults.${NC}"
fi

# Functions
deploy() {
  echo -e "${GREEN}Starting deployment...${NC}"
  
  # Build images
  echo "Building Docker images..."
  docker-compose build backend
  
  # Run migrations
  echo "Running database migrations..."
  docker-compose run --rm backend flask db upgrade
  
  # Initialize system
  echo "Initializing system wallets..."
  docker-compose run --rm backend python3 scripts/init_system.py
  
  # Start services
  echo "Starting services..."
  docker-compose up -d
  
  # Wait for health checks
  echo "Waiting for services to be healthy..."
  sleep 10
  
  # Verify deployment
  echo "Verifying deployment..."
  if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo "API available at: http://localhost:5001"
  else
    echo -e "${RED}❌ Deployment verification failed${NC}"
    docker-compose logs backend
    exit 1
  fi
}

migrate() {
  echo -e "${GREEN}Running database migrations...${NC}"
  docker-compose run --rm backend flask db upgrade
}

logs() {
  echo -e "${GREEN}Showing logs...${NC}"
  docker-compose logs -f backend
}

stop() {
  echo -e "${YELLOW}Stopping services...${NC}"
  docker-compose down
}

restart() {
  echo -e "${GREEN}Restarting services...${NC}"
  docker-compose restart backend
}

backup_db() {
  echo -e "${GREEN}Creating database backup...${NC}"
  BACKUP_FILE="backups/kingdompay_$(date +%Y%m%d_%H%M%S).sql"
  mkdir -p backups
  docker-compose exec -T postgres pg_dump -U admin kingdompay > "$BACKUP_FILE"
  echo "Backup saved to: $BACKUP_FILE"
}

# Main action dispatch
case $ACTION in
  deploy)
    deploy
    ;;
  migrate)
    migrate
    ;;
  logs)
    logs
    ;;
  stop)
    stop
    ;;
  restart)
    restart
    ;;
  backup)
    backup_db
    ;;
  *)
    echo "Usage: $0 [environment] [action]"
    echo "Actions: deploy, migrate, logs, stop, restart, backup"
    exit 1
    ;;
esac

