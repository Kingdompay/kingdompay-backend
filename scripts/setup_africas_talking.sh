#!/bin/bash
# Africa's Talking SMS Setup Script
# Helps configure Africa's Talking for KingdomPay

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Africa's Talking SMS Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if .env file exists
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    touch "$ENV_FILE"
fi

# Function to add or update env variable
add_env_var() {
    local key=$1
    local value=$2
    local comment=$3
    
    # Check if variable already exists
    if grep -q "^${key}=" "$ENV_FILE"; then
        # Update existing
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        else
            # Linux
            sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        fi
        echo -e "${GREEN}✅ Updated ${key}${NC}"
    else
        # Add new
        if [ -n "$comment" ]; then
            echo "" >> "$ENV_FILE"
            echo "# $comment" >> "$ENV_FILE"
        fi
        echo "${key}=${value}" >> "$ENV_FILE"
        echo -e "${GREEN}✅ Added ${key}${NC}"
    fi
}

echo -e "${YELLOW}📝 Please provide your Africa's Talking credentials:${NC}"
echo ""

# Get API Key
read -p "Enter your Africa's Talking API Key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ API Key is required${NC}"
    exit 1
fi

# Get Username
read -p "Enter your Africa's Talking Username (or 'sandbox' for testing): " USERNAME
if [ -z "$USERNAME" ]; then
    echo -e "${RED}❌ Username is required${NC}"
    exit 1
fi

# Get Environment
echo ""
echo "Select environment:"
echo "1) Sandbox (for testing)"
echo "2) Production"
read -p "Enter choice [1-2]: " ENV_CHOICE

case $ENV_CHOICE in
    1)
        API_URL="https://api.sandbox.africastalking.com/version1"
        USERNAME="sandbox"
        echo -e "${YELLOW}Using Sandbox environment${NC}"
        ;;
    2)
        API_URL="https://api.africastalking.com/version1"
        echo -e "${YELLOW}Using Production environment${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using Sandbox.${NC}"
        API_URL="https://api.sandbox.africastalking.com/version1"
        USERNAME="sandbox"
        ;;
esac

# Get Sender ID
read -p "Enter Sender ID [KingdomPay]: " SENDER_ID
SENDER_ID=${SENDER_ID:-KingdomPay}

# Add to .env
echo ""
echo -e "${YELLOW}📝 Updating .env file...${NC}"
echo ""

add_env_var "SMS_PROVIDER" "africastalking" "Africa's Talking SMS Configuration"
add_env_var "SMS_PROVIDER_API_KEY" "$API_KEY"
add_env_var "SMS_PROVIDER_URL" "$API_URL"
add_env_var "SMS_USERNAME" "$USERNAME"
add_env_var "SMS_SENDER_ID" "$SENDER_ID"
add_env_var "SMS_TIMEOUT" "30"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Configuration Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Test configuration: ${YELLOW}python3 scripts/test_sms_config.py${NC}"
echo "2. Test OTP sending: ${YELLOW}curl -X POST http://localhost:5001/api/v1/auth/otp/request -H 'Content-Type: application/json' -d '{\"phone_number\": \"+254712345678\"}'${NC}"
echo ""
echo "For sandbox testing:"
echo "- Register your phone number in Africa's Talking dashboard"
echo "- Only registered numbers can receive SMS in sandbox"
echo ""







