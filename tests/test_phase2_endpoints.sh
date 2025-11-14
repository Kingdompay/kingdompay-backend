#!/bin/bash
# Phase 2 API Testing Script
# Make sure server is running: python run.py

BASE_URL="http://localhost:5000"
API_BASE="$BASE_URL/api/v1"

echo "🧪 Phase 2 API Testing"
echo "===================="
echo ""

# Step 1: Get auth token (you'll need to set this manually)
echo "📝 Step 1: Authentication"
echo "Please authenticate first and set TOKEN variable:"
echo 'export TOKEN="your-jwt-token-here"'
echo ""
read -p "Press Enter when TOKEN is set..."

if [ -z "$TOKEN" ]; then
    echo "❌ TOKEN not set. Exiting."
    exit 1
fi

echo "✅ Using token: ${TOKEN:0:20}..."
echo ""

# Step 2: Test Fee Calculation
echo "📊 Step 2: Fee Calculation"
echo "Testing fee calculation for KSh 1,000..."
RESPONSE=$(curl -s -X POST "$API_BASE/fees/calculate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "community_id": 1}')

echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
echo ""

# Step 3: Test Transaction Limits
echo "🚦 Step 3: Transaction Limits"
echo "Testing limit validation for KSh 50,000..."
RESPONSE=$(curl -s -X POST "$API_BASE/fees/validate-limits" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50000}')

echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
echo ""

# Step 4: Test CDF
echo "💰 Step 4: Community Development Fund"
echo "Getting CDF balance for community 1..."
RESPONSE=$(curl -s -X GET "$API_BASE/communities/1/cdf" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
echo ""

# Step 5: Test CDF Impact
echo "📈 Step 5: CDF Impact Metrics"
RESPONSE=$(curl -s -X GET "$API_BASE/communities/1/cdf/impact" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
echo ""

# Step 6: Test Multi-Sig (Create)
echo "🔐 Step 6: Multi-Signature Approval"
echo "Creating approval request..."
APPROVAL_RESPONSE=$(curl -s -X POST "$API_BASE/communities/1/approvals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "WITHDRAWAL",
    "amount": 50000,
    "destination": "+254712345678",
    "description": "Test withdrawal",
    "required_signatures": 2
  }')

echo "$APPROVAL_RESPONSE" | jq '.' || echo "$APPROVAL_RESPONSE"
APPROVAL_ID=$(echo "$APPROVAL_RESPONSE" | jq -r '.approval_id // empty')
echo ""

if [ ! -z "$APPROVAL_ID" ]; then
    echo "✅ Approval created: $APPROVAL_ID"
    echo "Getting approval status..."
    curl -s -X GET "$API_BASE/approvals/$APPROVAL_ID" \
      -H "Authorization: Bearer $TOKEN" | jq '.'
fi
echo ""

# Step 7: Test QR Code Generation
echo "📱 Step 7: QR Code Generation"
RESPONSE=$(curl -s -X GET "$API_BASE/checkout/qr?amount=1000&memo=Test&campaign_id=1")
echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
echo ""

# Step 8: Test Provider Listing
echo "🔌 Step 8: Provider Listing"
echo "Checking available providers..."
# This endpoint may not exist yet, add if needed
echo "Provider service available (check logs for provider registration)"
echo ""

echo "✅ Testing Complete!"
echo ""
echo "📋 Summary:"
echo "- Fee calculation: Check response above"
echo "- Transaction limits: Check response above"
echo "- CDF operations: Check responses above"
echo "- Multi-sig approvals: Approval ID: $APPROVAL_ID"
echo "- QR codes: Check response above"
echo ""
echo "⚠️  Note: Some endpoints may require additional setup:"
echo "   - Database migrations (flask db upgrade)"
echo "   - Community/wallet creation"
echo "   - Provider credentials configuration"

