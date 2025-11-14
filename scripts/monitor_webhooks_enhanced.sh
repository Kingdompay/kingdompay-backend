#!/bin/bash
# Enhanced Webhook Monitoring Script
# Monitors M-Pesa webhooks, payment updates, and system events in real-time

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🔍 Enhanced Webhook & Payment Monitor${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${CYAN}Monitoring:${NC}"
echo "  - M-Pesa webhooks"
echo "  - Payment status updates"
echo "  - STK Push events"
echo "  - Wallet balance changes"
echo "  - Error events"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Check if using Docker
if command -v docker-compose &> /dev/null && [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    USE_DOCKER=true
    echo -e "${GREEN}✅ Using Docker logs${NC}"
else
    USE_DOCKER=false
    echo -e "${YELLOW}⚠️  Docker not detected, monitoring log files${NC}"
fi

echo ""

# Function to format log lines
format_log() {
    local line="$1"
    
    # M-Pesa webhook
    if echo "$line" | grep -qi "webhook.*mpesa\|mpesa.*webhook"; then
        echo -e "${CYAN}[WEBHOOK]${NC} $line"
    # Payment success
    elif echo "$line" | grep -qi "payment.*success\|status.*success"; then
        echo -e "${GREEN}[SUCCESS]${NC} $line"
    # Payment failed
    elif echo "$line" | grep -qi "payment.*failed\|status.*failed"; then
        echo -e "${RED}[FAILED]${NC} $line"
    # STK Push
    elif echo "$line" | grep -qi "stk.*push\|checkout.*request"; then
        echo -e "${MAGENTA}[STK PUSH]${NC} $line"
    # Wallet balance
    elif echo "$line" | grep -qi "wallet.*balance\|balance.*updated"; then
        echo -e "${BLUE}[WALLET]${NC} $line"
    # Error
    elif echo "$line" | grep -qi "error\|exception\|failed"; then
        echo -e "${RED}[ERROR]${NC} $line"
    # Default
    else
        echo "$line"
    fi
}

# Monitor function
monitor() {
    if [ "$USE_DOCKER" = true ]; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.yml" logs -f backend 2>&1 | \
            while IFS= read -r line; do
                if echo "$line" | grep -qi "mpesa\|webhook\|payment\|stk\|checkout\|wallet.*balance"; then
                    format_log "$line"
                fi
            done
    else
        # Monitor log files if they exist
        LOG_DIR="$PROJECT_ROOT/logs"
        if [ -d "$LOG_DIR" ]; then
            tail -f "$LOG_DIR"/*.log 2>/dev/null | \
                while IFS= read -r line; do
                    if echo "$line" | grep -qi "mpesa\|webhook\|payment\|stk\|checkout\|wallet.*balance"; then
                        format_log "$line"
                    fi
                done
        else
            echo -e "${RED}❌ No log files found${NC}"
            echo "Start the application to generate logs"
        fi
    fi
}

# Start monitoring
monitor

