#!/bin/bash
# Create a test payment and simulate webhook (Option 4 - Alternative approach)
# This creates a payment record directly and then simulates the webhook
# Useful for testing webhook processing without needing M-Pesa API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env
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
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🧪 Create Test Payment + Simulate Webhook${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Step 1: Authenticate
echo -e "${BLUE}1️⃣  Authenticating...${NC}"
TEST_PHONE="${TEST_PHONE:-+254708374149}"

# Request OTP
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d "{\"phone_number\": \"$TEST_PHONE\"}")

sleep 2
OTP_CODE=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" logs --tail=100 backend 2>/dev/null | grep -i "verification code" | grep "$TEST_PHONE" | tail -1 | grep -oE "[0-9]{6}" | tail -1)

if [ -z "$OTP_CODE" ]; then
    echo -e "${RED}❌ Could not get OTP${NC}"
    exit 1
fi

# Verify OTP
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/otp/verify" \
    -H "Content-Type: application/json" \
    -d "{\"phone_number\": \"$TEST_PHONE\", \"otp_code\": \"$OTP_CODE\", \"full_name\": \"Test User\"}")

if command -v jq &> /dev/null; then
    TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.access_token // empty')
    WALLET_ID=$(curl -s -X GET "$BASE_URL/api/v1/wallets/balance" -H "Authorization: Bearer $TOKEN" | jq -r '.wallet.id // empty')
else
    TOKEN=$(echo "$VERIFY_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    WALLET_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/wallets/balance" -H "Authorization: Bearer $TOKEN")
    WALLET_ID=$(echo "$WALLET_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated${NC}"
echo -e "${GREEN}✅ Wallet ID: $WALLET_ID${NC}"
echo ""

# Step 2: Create test payment via database
echo -e "${BLUE}2️⃣  Creating test payment...${NC}"
TEST_AMOUNT="${TEST_AMOUNT:-100}"
RANDOM_SUFFIX=$((RANDOM % 9000 + 1000))
CHECKOUT_ID="TEST$(date +%s)${RANDOM_SUFFIX}"

# Copy script to container and execute
docker cp "$PROJECT_ROOT/scripts/create_test_payment.py" "$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps -q backend):/tmp/create_test_payment.py" 2>/dev/null || true

PAYMENT_RESULT=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T backend python3 /tmp/create_test_payment.py "$WALLET_ID" "$TEST_AMOUNT" "$CHECKOUT_ID" 2>&1)

if echo "$PAYMENT_RESULT" | grep -q "ERROR"; then
    echo -e "${RED}❌ Failed to create payment: $PAYMENT_RESULT${NC}"
    exit 1
fi

PAYMENT_ID=$(echo "$PAYMENT_RESULT" | grep -o "SUCCESS:[0-9]*" | cut -d':' -f2)
echo -e "${GREEN}✅ Payment created: ID=$PAYMENT_ID, CheckoutRequestID=$CHECKOUT_ID${NC}"
echo ""

# Step 3: Simulate webhook
echo -e "${BLUE}3️⃣  Simulating M-Pesa webhook...${NC}"

WEBHOOK_PAYLOAD=$(cat <<EOF
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "test-merchant-$(date +%s)",
      "CheckoutRequestID": "${CHECKOUT_ID}",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {
            "Name": "Amount",
            "Value": ${TEST_AMOUNT}
          },
          {
            "Name": "MpesaReceiptNumber",
            "Value": "TEST$(echo $CHECKOUT_ID | cut -c1-8)"
          },
          {
            "Name": "TransactionDate",
            "Value": "$(date +%Y%m%d%H%M%S)"
          },
          {
            "Name": "PhoneNumber",
            "Value": "$(echo $TEST_PHONE | tr -d '+')"
          }
        ]
      }
    }
  }
}
EOF
)

echo "Sending webhook..."
WEBHOOK_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/webhooks/provider/MPESA" \
    -H "Content-Type: application/json" \
    -d "$WEBHOOK_PAYLOAD")

echo "Webhook Response: $WEBHOOK_RESPONSE"
echo ""

if echo "$WEBHOOK_RESPONSE" | grep -q "success.*true"; then
    echo -e "${GREEN}✅ Webhook processed successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Webhook response: $WEBHOOK_RESPONSE${NC}"
fi
echo ""

# Step 4: Verify results
echo -e "${BLUE}4️⃣  Verifying results...${NC}"
sleep 2

# Check payment status
PAYMENT_STATUS=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T backend python3 << PYEOF
from app import create_app
from extensions import db
from models.payment import Payment
import sys
import json

app = create_app()
with app.app_context():
    try:
        payment_id = int(sys.argv[1])
        payment = Payment.query.get(payment_id)
        if payment:
            print(json.dumps({
                "id": payment.id,
                "status": payment.status,
                "provider_ref": payment.provider_ref,
                "amount": float(payment.amount),
                "journal_id": payment.journal_id
            }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
PYEOF
    "$PAYMENT_ID" 2>&1)

echo "Payment Status: $PAYMENT_STATUS"

# Check wallet balance
WALLET_BALANCE=$(curl -s -X GET "$BASE_URL/api/v1/wallets/balance" \
    -H "Authorization: Bearer $TOKEN")

echo "Wallet Balance: $WALLET_BALANCE"
echo ""

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Test completed!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "Summary:"
echo "- Created test payment: ID=$PAYMENT_ID"
echo "- Simulated webhook with CheckoutRequestID: $CHECKOUT_ID"
echo "- Check payment status and wallet balance above"
echo ""

