#!/bin/bash
# Script to extract OTP from backend logs

echo "🔍 Searching for OTP in backend logs..."
echo ""

# Check recent logs for OTP
OTP_LINE=$(docker-compose logs --tail=500 backend 2>/dev/null | grep -i "SMS to\|verification code" | tail -1)

if [ -n "$OTP_LINE" ]; then
    echo "✅ Found OTP log entry:"
    echo "$OTP_LINE"
    echo ""
    
    # Try to extract OTP code (6 digits)
    OTP_CODE=$(echo "$OTP_LINE" | grep -oE '[0-9]{6}')
    
    if [ -n "$OTP_CODE" ]; then
        echo "📱 OTP Code: $OTP_CODE"
    else
        echo "⚠️  Could not extract OTP code from log"
        echo "Look for a 6-digit number in the log entry above"
    fi
else
    echo "❌ No OTP found in recent logs"
    echo ""
    echo "Try:"
    echo "1. Request a new OTP: curl -X POST http://localhost:5001/api/v1/auth/otp/request -H 'Content-Type: application/json' -d '{\"phone\": \"+254708374149\"}'"
    echo "2. Then check logs: docker-compose logs --tail=50 backend | grep -i 'SMS\|verification'"
fi

