#!/bin/bash
# Comprehensive M-Pesa Test Script
# Tests both STK Push and C2B functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            \#*|'') continue ;;
        esac
        export "$line" 2>/dev/null || true
    done < "$PROJECT_ROOT/.env"
    set +a
fi

BASE_URL=${BASE_URL:-http://localhost:5000}
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🧪 M-Pesa Integration Tests${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Check if server is running
echo -e "${CYAN}1️⃣  Checking server...${NC}"
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Server not running at $BASE_URL${NC}"
    echo "Start server with: python3 run.py or flask run"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Check M-Pesa credentials
echo -e "${CYAN}2️⃣  Checking M-Pesa configuration...${NC}"
if [ -z "$MPESA_CONSUMER_KEY" ] || [ -z "$MPESA_CONSUMER_SECRET" ]; then
    echo -e "${RED}❌ M-Pesa credentials not configured${NC}"
    exit 1
fi

if [ -z "$MPESA_SHORTCODE" ] || [ -z "$MPESA_PASSKEY" ]; then
    echo -e "${RED}❌ M-Pesa shortcode or passkey not configured${NC}"
    exit 1
fi

if [ -z "$MPESA_CALLBACK_URL" ]; then
    echo -e "${YELLOW}⚠️  MPESA_CALLBACK_URL not set${NC}"
else
    echo -e "${GREEN}✅ Callback URL: $MPESA_CALLBACK_URL${NC}"
fi

echo -e "${GREEN}✅ M-Pesa credentials configured${NC}"
echo ""

# Test menu
echo -e "${CYAN}Select test to run:${NC}"
echo "1. Test STK Push (Lipa na M-Pesa Online)"
echo "2. Test C2B URL Registration"
echo "3. Test C2B Payment Simulation"
echo "4. Run all tests"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}==========================================${NC}"
        echo -e "${BLUE}🧪 STK Push Test${NC}"
        echo -e "${BLUE}==========================================${NC}"
        echo ""
        echo -e "${YELLOW}Note: You need to authenticate first${NC}"
        echo "1. Request OTP: POST $BASE_URL/api/v1/auth/otp/request"
        echo "2. Verify OTP: POST $BASE_URL/api/v1/auth/otp/verify"
        echo "3. Use the access_token from response"
        echo ""
        read -p "Enter JWT token: " TOKEN
        
        if [ -z "$TOKEN" ]; then
            echo -e "${RED}❌ Token required${NC}"
            exit 1
        fi
        
        read -p "Enter phone number (default: +254708374149): " TEST_PHONE
        TEST_PHONE=${TEST_PHONE:-"+254708374149"}
        
        read -p "Enter amount (default: 100): " TEST_AMOUNT
        TEST_AMOUNT=${TEST_AMOUNT:-100}
        
        echo ""
        echo -e "${CYAN}Initiating STK Push...${NC}"
        RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/mpesa/pay" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"phone\": \"$TEST_PHONE\",
                \"amount\": $TEST_AMOUNT,
                \"account_reference\": \"TEST-$(date +%s)\",
                \"transaction_desc\": \"Test Payment\"
            }")
        
        echo "Response: $RESPONSE"
        echo ""
        
        if echo "$RESPONSE" | grep -q "\"success\":true"; then
            echo -e "${GREEN}✅ STK Push initiated successfully!${NC}"
            echo -e "${YELLOW}📱 Check your phone for the STK Push prompt${NC}"
        else
            echo -e "${RED}❌ STK Push failed${NC}"
            echo "Check the response above for error details"
        fi
        ;;
    2)
        echo ""
        echo -e "${BLUE}==========================================${NC}"
        echo -e "${BLUE}🧪 C2B URL Registration Test${NC}"
        echo -e "${BLUE}==========================================${NC}"
        echo ""
        python3 "$SCRIPT_DIR/test_c2b.py" --register
        ;;
    3)
        echo ""
        echo -e "${BLUE}==========================================${NC}"
        echo -e "${BLUE}🧪 C2B Payment Simulation Test${NC}"
        echo -e "${BLUE}==========================================${NC}"
        echo ""
        python3 "$SCRIPT_DIR/test_c2b.py" --simulate
        ;;
    4)
        echo ""
        echo -e "${BLUE}Running all tests...${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  Note: STK Push test requires manual authentication${NC}"
        echo "Skipping STK Push test. Run it manually with option 1."
        echo ""
        
        echo -e "${CYAN}Testing C2B URL Registration...${NC}"
        python3 "$SCRIPT_DIR/test_c2b.py" --register
        echo ""
        
        echo -e "${CYAN}Testing C2B Payment Simulation...${NC}"
        python3 "$SCRIPT_DIR/test_c2b.py" --simulate
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Tests completed${NC}"
echo -e "${GREEN}==========================================${NC}"

