#!/usr/bin/env bash
set -euo pipefail

# Color codes
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
NC=$'\033[0m'

echo "Checking Canton services..."

# Check Canton daemon process
if pgrep -f "canton.*daemon" > /dev/null || pgrep -f "canton.jar" > /dev/null; then
    echo "${GREEN}✓ Canton daemon is running${NC}"
else
    echo "${RED}✗ Canton daemon is NOT running${NC}"
    exit 1
fi

# Check JSON API process
if pgrep -f "json-api" > /dev/null; then
    echo "${GREEN}✓ JSON API process is running${NC}"
else
    echo "${YELLOW}! JSON API process is NOT running${NC}"
fi

# Check JSON API health endpoint
if curl -s -o /dev/null -w "%{http_code}" http://localhost:7575/livez 2>/dev/null | grep -q "200"; then
    echo "${GREEN}✓ JSON API is responding (health check passed)${NC}"
else
    echo "${RED}✗ JSON API is NOT responding${NC}"
fi

# Test party allocation to verify domain connection
echo "Testing domain connection..."
RESPONSE=$(curl -s -X POST http://localhost:7575/v1/parties/allocate \
    -H "Authorization: Bearer dummy" \
    -H "Content-Type: application/json" \
    -d '{"identifierHint": "health_check_test", "displayName": "Health Check Test"}' 2>/dev/null || echo "")

if echo "$RESPONSE" | grep -q "identifier"; then
    echo "${GREEN}✓ Domain connection is working (party allocation successful)${NC}"
elif echo "$RESPONSE" | grep -q "PARTY_ALLOCATION_WITHOUT_CONNECTED_DOMAIN"; then
    echo "${RED}✗ Domain connection FAILED - participant not connected to domain${NC}"
    echo "Response: $RESPONSE"
    exit 1
else
    echo "${YELLOW}! Unexpected response from party allocation test${NC}"
    echo "Response: $RESPONSE"
fi

echo ""
echo "Service URLs:"
echo "  Canton Admin API: http://localhost:10012"
echo "  Canton Ledger API: localhost:10011"
echo "  JSON API: http://localhost:7575"