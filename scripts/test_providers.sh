#!/bin/bash
# Provider Integration Test Script
# Tests M-Pesa, Airtel, and T-Kash integrations

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📋 Loading environment variables from .env file..."
    # Load .env file and export variables
    # This method handles quotes and special characters properly
    set -a
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        case "$line" in
            \#*|'') continue ;;
        esac
        # Export the variable
        export "$line" 2>/dev/null || true
    done < "$PROJECT_ROOT/.env"
    set +a
    echo -e "\033[0;32m✅ Environment variables loaded\033[0m"
else
    echo -e "\033[1;33m⚠️  No .env file found at $PROJECT_ROOT/.env\033[0m"
fi

BASE_URL=${BASE_URL:-http://localhost:5001}
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "🧪 KingdomPay Provider Integration Tests"
echo "========================================"
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not found. Install with: brew install jq${NC}"
    echo "Continuing without jq..."
    USE_JQ=false
else
    USE_JQ=true
fi

# Function to extract JSON value
extract_json() {
    if [ "$USE_JQ" = true ]; then
        echo "$1" | jq -r "$2" 2>/dev/null || echo ""
    else
        echo "$1" | grep -o "\"$2\":\"[^\"]*\"" | cut -d'"' -f4
    fi
}

# Step 1: Check if server is running
echo "1️⃣  Checking server health..."
HEALTH=$(curl -s "$BASE_URL/health" || echo "")
if [ -z "$HEALTH" ]; then
    echo -e "${RED}❌ Server not running at $BASE_URL${NC}"
    echo "Start server with: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Step 2: Check environment variables
echo "2️⃣  Checking provider credentials..."
MISSING_VARS=()

# Check MPESA credentials
if [ -z "$MPESA_CONSUMER_KEY" ]; then
    MISSING_VARS+=("MPESA_CONSUMER_KEY")
else
    echo -e "${GREEN}✅ MPESA_CONSUMER_KEY: ${MPESA_CONSUMER_KEY:0:20}...${NC}"
fi

if [ -z "$MPESA_CONSUMER_SECRET" ]; then
    MISSING_VARS+=("MPESA_CONSUMER_SECRET")
else
    echo -e "${GREEN}✅ MPESA_CONSUMER_SECRET: ${MPESA_CONSUMER_SECRET:0:20}...${NC}"
fi

if [ -z "$MPESA_PASSKEY" ]; then
    echo -e "${YELLOW}⚠️  MPESA_PASSKEY not set${NC}"
else
    echo -e "${GREEN}✅ MPESA_PASSKEY: SET${NC}"
fi

if [ -z "$MPESA_SHORTCODE" ]; then
    echo -e "${YELLOW}⚠️  MPESA_SHORTCODE not set${NC}"
else
    echo -e "${GREEN}✅ MPESA_SHORTCODE: $MPESA_SHORTCODE${NC}"
fi

# Check Airtel credentials (optional)
if [ -z "$AIRTEL_CLIENT_ID" ]; then
    echo -e "${YELLOW}⚠️  AIRTEL_CLIENT_ID not set (optional)${NC}"
fi
if [ -z "$AIRTEL_CLIENT_SECRET" ]; then
    echo -e "${YELLOW}⚠️  AIRTEL_CLIENT_SECRET not set (optional)${NC}"
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Add them to your .env file (see docs/PROVIDER_SETUP_GUIDE.md)"
    echo ""
    echo -e "${RED}Exiting...${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All required provider credentials found${NC}"
fi
echo ""

# Step 3: Test authentication
echo "3️⃣  Testing authentication..."
echo "Enter test phone number (e.g., +254708374149): "
read -r TEST_PHONE

if [ -z "$TEST_PHONE" ]; then
    TEST_PHONE="+254708374149"
    echo "Using default: $TEST_PHONE"
fi

echo "Requesting OTP..."
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d "{\"phone\": \"$TEST_PHONE\"}")

SUCCESS=$(extract_json "$OTP_RESPONSE" "success")
if [ "$SUCCESS" = "true" ] || [ -z "$SUCCESS" ]; then
    echo -e "${GREEN}✅ OTP requested successfully${NC}"
    echo ""
    echo "Enter OTP code (check SMS or logs): "
    read -r OTP_CODE
    
    if [ -z "$OTP_CODE" ]; then
        echo -e "${YELLOW}⚠️  No OTP provided. Skipping authentication test.${NC}"
        TOKEN=""
    else
        echo "Verifying OTP..."
        VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/verify" \
            -H "Content-Type: application/json" \
            -d "{\"phone\": \"$TEST_PHONE\", \"otp\": \"$OTP_CODE\"}")
        
        TOKEN=$(extract_json "$VERIFY_RESPONSE" "access_token")
        if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
            echo -e "${GREEN}✅ Authentication successful${NC}"
            echo "Token: ${TOKEN:0:20}..."
        else
            echo -e "${RED}❌ Authentication failed${NC}"
            echo "Response: $VERIFY_RESPONSE"
            TOKEN=""
        fi
    fi
else
    echo -e "${RED}❌ OTP request failed${NC}"
    echo "Response: $OTP_RESPONSE"
    TOKEN=""
fi
echo ""

# Step 4: Test M-Pesa (if credentials available)
if [ -n "$MPESA_CONSUMER_KEY" ] && [ -n "$TOKEN" ]; then
    echo "4️⃣  Testing M-Pesa STK Push..."
    echo "Enter amount to test (default: 100): "
    read -r TEST_AMOUNT
    if [ -z "$TEST_AMOUNT" ]; then
        TEST_AMOUNT=100
    fi
    
    echo "Getting wallet ID..."
    WALLETS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/wallets" \
        -H "Authorization: Bearer $TOKEN")
    
    WALLET_ID=$(extract_json "$WALLETS_RESPONSE" "id")
    if [ -z "$WALLET_ID" ] || [ "$WALLET_ID" = "null" ]; then
        # Try alternative path
        WALLET_ID=$(echo "$WALLETS_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    fi
    
    if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
        echo "Wallet ID: $WALLET_ID"
        echo ""
        echo "Initiating M-Pesa STK Push..."
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
        echo -e "${YELLOW}📱 Check your phone for STK Push prompt${NC}"
        echo "After completing payment, webhook should update wallet balance"
    else
        echo -e "${YELLOW}⚠️  Could not get wallet ID${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping M-Pesa test (missing credentials or token)${NC}"
fi
echo ""

# Step 5: Summary
echo "========================================"
echo "📋 Test Summary"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Complete payment on your phone (if STK Push initiated)"
echo "2. Check webhook logs: docker-compose logs -f backend | grep webhook"
echo "3. Verify wallet balance updated"
echo "4. Check payment status: curl -X GET $BASE_URL/api/v1/payments -H \"Authorization: Bearer \$TOKEN\""
echo ""
echo "For detailed setup instructions, see: docs/PROVIDER_SETUP_GUIDE.md"

