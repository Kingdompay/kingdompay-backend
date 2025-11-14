#!/bin/bash
# Start KingdomPay backend with ngrok tunnel for M-Pesa callbacks
# This script sets up ngrok and starts the backend services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🚀 Starting KingdomPay with ngrok${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Setup ngrok first
echo -e "${BLUE}1️⃣  Setting up ngrok tunnel...${NC}"
"$SCRIPT_DIR/setup_ngrok_callback.sh"

# Wait a moment for ngrok to be ready
sleep 2

# Start backend services
echo ""
echo -e "${BLUE}2️⃣  Starting backend services...${NC}"
cd "$PROJECT_ROOT"

if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo -e "${GREEN}✅ Backend services started${NC}"
    echo ""
    echo "View logs: ${YELLOW}docker-compose logs -f backend${NC}"
    echo "Stop services: ${YELLOW}docker-compose down${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose not found. Starting Flask directly...${NC}"
    echo "Make sure to set FLASK_ENV and other environment variables"
    flask run --host=0.0.0.0 --port=5001
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}📋 Useful commands:${NC}"
echo "  View ngrok dashboard: ${YELLOW}open http://localhost:4040${NC}"
echo "  Check callback URL: ${YELLOW}grep MPESA_CALLBACK_URL .env${NC}"
echo "  Test STK Push: ${YELLOW}./test_real_stk_push.sh${NC}"
echo ""

