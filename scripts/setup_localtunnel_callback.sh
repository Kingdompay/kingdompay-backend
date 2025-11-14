#!/bin/bash
# Setup LocalTunnel for M-Pesa callback URL (alternative to ngrok)
# LocalTunnel is free and often works when ngrok-free.dev is blocked

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🔗 Setting up LocalTunnel for M-Pesa${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Check if localtunnel is installed
if ! command -v lt &> /dev/null; then
    echo -e "${YELLOW}⚠️  LocalTunnel not installed${NC}"
    echo ""
    echo "Install with:"
    echo "  ${YELLOW}npm install -g localtunnel${NC}"
    echo ""
    echo "Or use ngrok instead:"
    echo "  ${YELLOW}./scripts/setup_ngrok_callback.sh${NC}"
    exit 1
fi

# Check if localtunnel is already running
if pgrep -f "lt --port 5001" > /dev/null; then
    echo -e "${YELLOW}⚠️  LocalTunnel is already running on port 5001${NC}"
    echo "Stopping existing tunnel..."
    pkill -f "lt --port 5001" || true
    sleep 2
fi

# Start LocalTunnel
echo -e "${BLUE}🚀 Starting LocalTunnel...${NC}"
echo "This will give you a public URL. Press Ctrl+C after you see the URL."
echo ""

# Start localtunnel in background and capture output
lt --port 5001 > /tmp/localtunnel_output.txt 2>&1 &
LT_PID=$!

# Wait for URL
sleep 5

# Extract URL from output
TUNNEL_URL=$(grep -o "https://[^ ]*\.loca\.lt" /tmp/localtunnel_output.txt 2>/dev/null | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}❌ Failed to get LocalTunnel URL${NC}"
    echo "Check output: cat /tmp/localtunnel_output.txt"
    kill $LT_PID 2>/dev/null || true
    exit 1
fi

CALLBACK_URL="${TUNNEL_URL}/api/v1/webhooks/provider/MPESA"

echo -e "${GREEN}✅ LocalTunnel started: $TUNNEL_URL${NC}"
echo -e "${GREEN}✅ Callback URL: $CALLBACK_URL${NC}"
echo ""

# Save PID
echo $LT_PID > /tmp/localtunnel_kingdompay.pid

# Update .env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from env.example...${NC}"
    if [ -f "$PROJECT_ROOT/env.example" ]; then
        cp "$PROJECT_ROOT/env.example" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi
fi

# Update or add MPESA_CALLBACK_URL
if grep -q "^MPESA_CALLBACK_URL=" "$ENV_FILE"; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^MPESA_CALLBACK_URL=.*|MPESA_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    else
        sed -i "s|^MPESA_CALLBACK_URL=.*|MPESA_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    fi
    echo -e "${GREEN}✅ Updated MPESA_CALLBACK_URL in .env${NC}"
else
    echo "" >> "$ENV_FILE"
    echo "# M-Pesa Callback URL (auto-configured by LocalTunnel)" >> "$ENV_FILE"
    echo "MPESA_CALLBACK_URL=$CALLBACK_URL" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added MPESA_CALLBACK_URL to .env${NC}"
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ LocalTunnel setup complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Restart backend: ${YELLOW}docker-compose restart backend${NC}"
echo "2. Test STK Push: ${YELLOW}./test_real_stk_push.sh${NC}"
echo ""
echo -e "${YELLOW}⚠️  Keep LocalTunnel running (PID: $LT_PID)${NC}"
echo "   To stop: ${YELLOW}kill $LT_PID${NC} or ${YELLOW}pkill -f 'lt --port 5001'${NC}"
echo ""


