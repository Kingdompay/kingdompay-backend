#!/bin/bash
# Quick STK Push Test Script
# Follows the MPESA_READY_TO_TEST.md guide

set -e

BASE_URL=${BASE_URL:-http://localhost:5001}
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Quick STK Push Test${NC}"
echo "======================"
echo ""

# Check if server is running
echo -e "${YELLOW}1. Checking server...${NC}"
if ! curl -s "$BASE_URL/health" > /dev/null; then
    echo -e "${RED}❌ Server not running at $BASE_URL${NC}"
    echo "Start with: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Get test phone number
echo -e "${YELLOW}2. Enter test phone number (default: +254708374149):${NC}"
read -r TEST_PHONE
if [ -z "$TEST_PHONE" ]; then
    TEST_PHONE="+254708374149"
fi
echo "Using: $TEST_PHONE"
echo ""

# Request OTP
echo -e "${YELLOW}3. Requesting OTP...${NC}"
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d "{\"phone\": \"$TEST_PHONE\"}")

if echo "$OTP_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ OTP requested${NC}"
else
    echo -e "${RED}❌ OTP request failed${NC}"
    echo "$OTP_RESPONSE"
    exit 1
fi
echo ""

# Get OTP code
echo -e "${YELLOW}4. Enter OTP code (check SMS or logs):${NC}"
read -r OTP_CODE

if [ -z "$OTP_CODE" ]; then
    echo -e "${RED}❌ OTP code required${NC}"
    exit 1
fi

# Get full name (required for new users)
echo -e "${YELLOW}5. Enter your full name (required for new users, optional for existing):${NC}"
read -r FULL_NAME
if [ -z "$FULL_NAME" ]; then
    FULL_NAME="Test User"
    echo "Using default: $FULL_NAME"
fi

# Verify OTP
echo -e "${YELLOW}6. Verifying OTP...${NC}"
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/verify" \
    -H "Content-Type: application/json" \
    -d "{\"phone_number\": \"$TEST_PHONE\", \"otp_code\": \"$OTP_CODE\", \"full_name\": \"$FULL_NAME\"}")

# Extract token (try jq first, then grep)
if command -v jq &> /dev/null; then
    TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.access_token // empty')
else
    TOKEN=$(echo "$VERIFY_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ] || [ "$TOKEN" = "" ]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "Response: $VERIFY_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated${NC}"
echo "Token: ${TOKEN:0:30}..."
echo ""

# Get wallet ID
echo -e "${YELLOW}6. Getting wallet ID...${NC}"
WALLETS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/wallets" \
    -H "Authorization: Bearer $TOKEN")

if command -v jq &> /dev/null; then
    WALLET_ID=$(echo "$WALLETS_RESPONSE" | jq -r '.wallets[0].id // .id // empty')
    if [ -z "$WALLET_ID" ]; then
        WALLET_ID=$(echo "$WALLETS_RESPONSE" | jq -r '.[] | select(.id) | .id' | head -1)
    fi
else
    WALLET_ID=$(echo "$WALLETS_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
fi

if [ -z "$WALLET_ID" ] || [ "$WALLET_ID" = "null" ]; then
    echo -e "${YELLOW}⚠️  Could not get wallet ID from response${NC}"
    echo "Response: $WALLETS_RESPONSE"
    echo ""
    echo "Please enter wallet ID manually:"
    read -r WALLET_ID
fi

if [ -z "$WALLET_ID" ]; then
    echo -e "${RED}❌ Wallet ID required${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Wallet ID: $WALLET_ID${NC}"
echo ""

# Get amount
echo -e "${YELLOW}8. Enter amount to test (default: 100):${NC}"
read -r TEST_AMOUNT
if [ -z "$TEST_AMOUNT" ]; then
    TEST_AMOUNT=100
fi
echo ""

# Initiate STK Push
echo -e "${YELLOW}9. Initiating STK Push...${NC}"
STK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/topups/momo" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"amount\": $TEST_AMOUNT,
        \"phone\": \"$TEST_PHONE\",
        \"provider\": \"MPESA\",
        \"wallet_id\": $WALLET_ID
    }")

echo "Response: $STK_RESPONSE"
echo ""

if echo "$STK_RESPONSE" | grep -q "success\|initiated\|checkout"; then
    echo -e "${GREEN}✅ STK Push initiated!${NC}"
    echo ""
    echo -e "${BLUE}📱 Next steps:${NC}"
    echo "1. Check your phone for STK Push prompt"
    echo "2. Enter your M-Pesa PIN to complete payment"
    echo "3. Wait for webhook to update wallet balance"
    echo ""
    echo -e "${YELLOW}To check payment status:${NC}"
    echo "curl -X GET $BASE_URL/api/v1/payments -H \"Authorization: Bearer $TOKEN\""
    echo ""
    echo -e "${YELLOW}To check wallet balance:${NC}"
    echo "curl -X GET $BASE_URL/api/v1/wallets/$WALLET_ID -H \"Authorization: Bearer $TOKEN\""
else
    echo -e "${RED}❌ STK Push failed${NC}"
    echo "Check the response above for error details"
    exit 1
fi

