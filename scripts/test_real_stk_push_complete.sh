#!/bin/bash
# Complete Real M-Pesa STK Push Test Script
# Tests the full end-to-end payment flow with real M-Pesa transactions

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

BASE_URL=${BASE_URL:-http://localhost:5001}
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🧪 Real M-Pesa STK Push Test${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq not found. Install with: brew install jq${NC}"
    USE_JQ=false
else
    USE_JQ=true
fi

extract_json() {
    if [ "$USE_JQ" = true ]; then
        echo "$1" | jq -r "$2" 2>/dev/null || echo ""
    else
        echo "$1" | grep -o "\"$2\":\"[^\"]*\"" | cut -d'"' -f4
    fi
}

# Step 1: Check server
echo -e "${CYAN}1️⃣  Checking server health...${NC}"
HEALTH=$(curl -s "$BASE_URL/health" || echo "")
if [ -z "$HEALTH" ]; then
    echo -e "${RED}❌ Server not running at $BASE_URL${NC}"
    echo "Start server with: docker-compose up -d or flask run"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Step 2: Check M-Pesa credentials
echo -e "${CYAN}2️⃣  Verifying M-Pesa credentials...${NC}"
if [ -z "$MPESA_CONSUMER_KEY" ] || [ -z "$MPESA_CONSUMER_SECRET" ]; then
    echo -e "${RED}❌ M-Pesa credentials not configured${NC}"
    exit 1
fi
echo -e "${GREEN}✅ M-Pesa credentials configured${NC}"
echo ""

# Step 3: Get phone number
echo -e "${CYAN}3️⃣  Enter phone number${NC}"
echo -e "${YELLOW}   Format: +254712345678 or 0712345678${NC}"
read -p "Phone number: " TEST_PHONE

# Normalize phone number
TEST_PHONE=$(echo "$TEST_PHONE" | tr -d ' ')
if [[ ! "$TEST_PHONE" =~ ^\+254 ]]; then
    if [[ "$TEST_PHONE" =~ ^0 ]]; then
        TEST_PHONE="+254${TEST_PHONE:1}"
    else
        TEST_PHONE="+254$TEST_PHONE"
    fi
fi

echo -e "${GREEN}✅ Using phone: $TEST_PHONE${NC}"
echo ""

# Step 4: Request OTP
echo -e "${CYAN}4️⃣  Requesting OTP...${NC}"
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d "{\"phone_number\": \"$TEST_PHONE\"}")

if echo "$OTP_RESPONSE" | grep -q "success.*true\|message"; then
    echo -e "${GREEN}✅ OTP requested successfully${NC}"
else
    echo -e "${RED}❌ OTP request failed${NC}"
    echo "Response: $OTP_RESPONSE"
    exit 1
fi

# Get OTP from logs (if using Docker)
if command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}   Checking logs for OTP code...${NC}"
    sleep 2
    OTP_CODE=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" logs --tail=100 backend 2>/dev/null | \
        grep -i "verification code\|OTP" | grep "$TEST_PHONE" | tail -1 | grep -oE "[0-9]{6}" | tail -1)
    
    if [ -n "$OTP_CODE" ]; then
        echo -e "${GREEN}   Found OTP in logs: $OTP_CODE${NC}"
    fi
fi

echo ""
read -p "Enter OTP code: " OTP_CODE
echo ""

# Step 5: Verify OTP
echo -e "${CYAN}5️⃣  Verifying OTP...${NC}"
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/verify" \
    -H "Content-Type: application/json" \
    -d "{\"phone_number\": \"$TEST_PHONE\", \"otp_code\": \"$OTP_CODE\"}")

if [ "$USE_JQ" = true ]; then
    TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.access_token // .token // empty' 2>/dev/null)
    SUCCESS=$(echo "$VERIFY_RESPONSE" | jq -r '.success // false' 2>/dev/null)
else
    TOKEN=$(echo "$VERIFY_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    SUCCESS=$(echo "$VERIFY_RESPONSE" | grep -q "success.*true" && echo "true" || echo "false")
fi

if [ -z "$TOKEN" ] || [ "$SUCCESS" != "true" ]; then
    echo -e "${RED}❌ OTP verification failed${NC}"
    echo "Response: $VERIFY_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ OTP verified successfully${NC}"
echo -e "${GREEN}✅ Access token obtained${NC}"
echo ""

# Step 6: Get wallet ID
echo -e "${CYAN}6️⃣  Getting wallet information...${NC}"
WALLETS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/wallets" \
    -H "Authorization: Bearer $TOKEN")

if [ "$USE_JQ" = true ]; then
    WALLET_ID=$(echo "$WALLETS_RESPONSE" | jq -r '.[0].id // .id // empty' 2>/dev/null)
    WALLET_BALANCE=$(echo "$WALLETS_RESPONSE" | jq -r '.[0].balance // .balance // 0' 2>/dev/null)
else
    WALLET_ID=$(echo "$WALLETS_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    WALLET_BALANCE=$(echo "$WALLETS_RESPONSE" | grep -o '"balance":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

if [ -z "$WALLET_ID" ] || [ "$WALLET_ID" = "null" ]; then
    echo -e "${RED}❌ Could not get wallet ID${NC}"
    echo "Response: $WALLETS_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Wallet ID: $WALLET_ID${NC}"
echo -e "${GREEN}✅ Current Balance: $WALLET_BALANCE${NC}"
echo ""

# Step 7: Get amount
echo -e "${CYAN}7️⃣  Enter payment amount${NC}"
read -p "Amount (KES): " TEST_AMOUNT

if ! [[ "$TEST_AMOUNT" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo -e "${RED}❌ Invalid amount${NC}"
    exit 1
fi

echo ""

# Step 8: Initiate STK Push
echo -e "${CYAN}8️⃣  Initiating M-Pesa STK Push...${NC}"
echo -e "${YELLOW}   Amount: KES $TEST_AMOUNT${NC}"
echo -e "${YELLOW}   Phone: $TEST_PHONE${NC}"
echo ""

STK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/topups/momo" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"amount\": $TEST_AMOUNT,
        \"phone\": \"$TEST_PHONE\",
        \"provider\": \"MPESA\",
        \"wallet_id\": $WALLET_ID
    }")

if [ "$USE_JQ" = true ]; then
    PAYMENT_ID=$(echo "$STK_RESPONSE" | jq -r '.payment_id // .id // empty' 2>/dev/null)
    STK_SUCCESS=$(echo "$STK_RESPONSE" | jq -r '.success // false' 2>/dev/null)
    STK_MESSAGE=$(echo "$STK_RESPONSE" | jq -r '.message // ""' 2>/dev/null)
else
    PAYMENT_ID=$(echo "$STK_RESPONSE" | grep -o '"payment_id":[0-9]*' | cut -d':' -f2)
    STK_SUCCESS=$(echo "$STK_RESPONSE" | grep -q "success.*true" && echo "true" || echo "false")
fi

if [ "$STK_SUCCESS" != "true" ] || [ -z "$PAYMENT_ID" ]; then
    echo -e "${RED}❌ STK Push initiation failed${NC}"
    echo "Response: $STK_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ STK Push initiated successfully${NC}"
echo -e "${GREEN}✅ Payment ID: $PAYMENT_ID${NC}"
echo ""
echo -e "${YELLOW}📱 CHECK YOUR PHONE NOW!${NC}"
echo -e "${YELLOW}   You should receive an M-Pesa STK Push prompt${NC}"
echo -e "${YELLOW}   Enter your M-Pesa PIN to complete the payment${NC}"
echo ""

# Step 9: Monitor payment status
echo -e "${CYAN}9️⃣  Monitoring payment status...${NC}"
echo -e "${YELLOW}   Waiting for payment completion...${NC}"
echo ""

MAX_WAIT=120  # 2 minutes
WAIT_TIME=0
INTERVAL=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    sleep $INTERVAL
    WAIT_TIME=$((WAIT_TIME + INTERVAL))
    
    PAYMENT_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/payments" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ "$USE_JQ" = true ]; then
        PAYMENT_STATUS=$(echo "$PAYMENT_RESPONSE" | jq -r ".[] | select(.id == $PAYMENT_ID) | .status // empty" 2>/dev/null)
    else
        PAYMENT_STATUS=$(echo "$PAYMENT_RESPONSE" | grep -A 10 "\"id\":$PAYMENT_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    fi
    
    if [ "$PAYMENT_STATUS" = "SUCCESS" ]; then
        echo -e "${GREEN}✅ Payment completed successfully!${NC}"
        break
    elif [ "$PAYMENT_STATUS" = "FAILED" ]; then
        echo -e "${RED}❌ Payment failed${NC}"
        break
    else
        echo -e "${YELLOW}   Status: ${PAYMENT_STATUS:-PENDING} (waiting ${WAIT_TIME}s)...${NC}"
    fi
done

# Step 10: Verify wallet balance
echo ""
echo -e "${CYAN}🔟 Verifying wallet balance...${NC}"
sleep 2

WALLETS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/wallets" \
    -H "Authorization: Bearer $TOKEN")

if [ "$USE_JQ" = true ]; then
    NEW_BALANCE=$(echo "$WALLETS_RESPONSE" | jq -r ".[] | select(.id == $WALLET_ID) | .balance // .[0].balance // 0" 2>/dev/null)
else
    NEW_BALANCE=$(echo "$WALLETS_RESPONSE" | grep -A 5 "\"id\":$WALLET_ID" | grep -o '"balance":"[^"]*"' | cut -d'"' -f4)
fi

echo -e "${GREEN}✅ New Balance: $NEW_BALANCE${NC}"

if [ "$PAYMENT_STATUS" = "SUCCESS" ]; then
    echo ""
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}✅ TEST COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo "Summary:"
    echo "  - Payment ID: $PAYMENT_ID"
    echo "  - Amount: KES $TEST_AMOUNT"
    echo "  - Status: SUCCESS"
    echo "  - Balance Before: $WALLET_BALANCE"
    echo "  - Balance After: $NEW_BALANCE"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠️  Payment status: ${PAYMENT_STATUS:-PENDING}${NC}"
    echo "Check payment status manually:"
    echo "  curl -X GET $BASE_URL/api/v1/payments -H \"Authorization: Bearer $TOKEN\""
fi

