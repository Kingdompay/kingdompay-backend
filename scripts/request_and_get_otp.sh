#!/bin/bash
# Request OTP and extract it from logs

PHONE=${1:-"+254708374149"}

echo "📱 Requesting OTP for $PHONE..."
echo ""

# Request OTP
curl -s -X POST http://localhost:5001/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d "{\"phone_number\": \"$PHONE\"}" > /dev/null

# Wait a moment for logs to be written
sleep 2

# Extract OTP from logs (look for the pattern in logs)
OTP=$(docker-compose logs --tail=20 backend 2>/dev/null | \
  grep -i "Your KingdomPay verification code is" | \
  tail -1 | \
  grep -oE '[0-9]{6}' | \
  tail -1)

if [ -n "$OTP" ]; then
    echo "✅ OTP Code: $OTP"
    echo ""
    echo "Use this to verify:"
    echo "curl -X POST http://localhost:5001/api/v1/auth/otp/verify \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"phone_number\": \"$PHONE\", \"otp_code\": \"$OTP\", \"full_name\": \"Test User\"}'"
else
    echo "❌ Could not find OTP in logs"
    echo ""
    echo "Try checking logs manually:"
    echo "docker-compose logs --tail=20 backend | grep -i 'verification code'"
fi

