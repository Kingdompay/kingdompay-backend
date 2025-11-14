#!/bin/bash
# Setup ngrok tunnel for M-Pesa callback URL
# This script starts ngrok and updates MPESA_CALLBACK_URL in .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🔗 Setting up ngrok for M-Pesa Callbacks${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}❌ ngrok is not installed${NC}"
    echo ""
    echo "Install ngrok:"
    echo "  macOS:   brew install ngrok"
    echo "  Linux:   Download from https://ngrok.com/download"
    echo "  Windows: Download from https://ngrok.com/download"
    echo ""
    echo "Or sign up at https://dashboard.ngrok.com/get-started/setup"
    exit 1
fi

# Check if ngrok is already running
if pgrep -x "ngrok" > /dev/null; then
    echo -e "${YELLOW}⚠️  ngrok is already running${NC}"
    echo ""
    echo "Checking existing ngrok tunnels..."
    
    # Try to get the public URL from ngrok API
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}✅ Found existing ngrok tunnel: $NGROK_URL${NC}"
        CALLBACK_URL="${NGROK_URL}/api/v1/webhooks/provider/MPESA"
        echo -e "${GREEN}✅ Callback URL: $CALLBACK_URL${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not detect ngrok tunnel URL${NC}"
        echo "Please stop ngrok and run this script again, or manually set MPESA_CALLBACK_URL"
        exit 1
    fi
else
    # Start ngrok in background
    echo -e "${BLUE}🚀 Starting ngrok tunnel...${NC}"
    
    # Kill any existing ngrok processes on port 4040
    lsof -ti:4040 | xargs kill -9 2>/dev/null || true
    
    # Start ngrok
    ngrok http 5001 > /dev/null 2>&1 &
    NGROK_PID=$!
    
    # Wait for ngrok to start
    echo "Waiting for ngrok to start..."
    sleep 3
    
    # Get the public URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -z "$NGROK_URL" ]; then
        echo -e "${RED}❌ Failed to get ngrok URL${NC}"
        echo "Make sure ngrok is authenticated: ngrok config add-authtoken YOUR_TOKEN"
        kill $NGROK_PID 2>/dev/null || true
        exit 1
    fi
    
    echo -e "${GREEN}✅ ngrok tunnel started: $NGROK_URL${NC}"
    CALLBACK_URL="${NGROK_URL}/api/v1/webhooks/provider/MPESA"
    echo -e "${GREEN}✅ Callback URL: $CALLBACK_URL${NC}"
    
    # Save ngrok PID for cleanup
    echo $NGROK_PID > /tmp/ngrok_kingdompay.pid
fi

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
    # Update existing entry
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^MPESA_CALLBACK_URL=.*|MPESA_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    else
        # Linux
        sed -i "s|^MPESA_CALLBACK_URL=.*|MPESA_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    fi
    echo -e "${GREEN}✅ Updated MPESA_CALLBACK_URL in .env${NC}"
else
    # Add new entry
    echo "" >> "$ENV_FILE"
    echo "# M-Pesa Callback URL (auto-configured by ngrok)" >> "$ENV_FILE"
    echo "MPESA_CALLBACK_URL=$CALLBACK_URL" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added MPESA_CALLBACK_URL to .env${NC}"
fi

# Also update MPESA_B2C_CALLBACK_URL if it exists
if grep -q "^MPESA_B2C_CALLBACK_URL=" "$ENV_FILE"; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^MPESA_B2C_CALLBACK_URL=.*|MPESA_B2C_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    else
        sed -i "s|^MPESA_B2C_CALLBACK_URL=.*|MPESA_B2C_CALLBACK_URL=$CALLBACK_URL|" "$ENV_FILE"
    fi
    echo -e "${GREEN}✅ Updated MPESA_B2C_CALLBACK_URL in .env${NC}"
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ ngrok setup complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Restart your backend to load the new callback URL:"
echo "   ${YELLOW}docker-compose restart backend${NC}"
echo ""
echo "2. Verify the callback URL is set:"
echo "   ${YELLOW}grep MPESA_CALLBACK_URL .env${NC}"
echo ""
echo "3. Test M-Pesa STK Push:"
echo "   ${YELLOW}./test_real_stk_push.sh${NC}"
echo ""
echo -e "${YELLOW}⚠️  Note: Keep this terminal open to maintain the ngrok tunnel${NC}"
echo "   Or run ngrok in a separate terminal: ${YELLOW}ngrok http 5001${NC}"
echo ""
echo "To stop ngrok: ${YELLOW}pkill ngrok${NC} or ${YELLOW}kill \$(cat /tmp/ngrok_kingdompay.pid)${NC}"

