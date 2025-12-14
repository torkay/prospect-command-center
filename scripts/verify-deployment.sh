#!/bin/bash
# =============================================================================
# Prospect Command Center - Deployment Verification Script
# =============================================================================
# Usage: ./scripts/verify-deployment.sh https://your-app.up.railway.app
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL (default to localhost)
BASE_URL=${1:-"http://localhost:8000"}

echo "=============================================="
echo "  Prospect Command Center - Deploy Check"
echo "=============================================="
echo ""
echo "Target: $BASE_URL"
echo ""

# Track failures
FAILED=0

# Function to check endpoint
check_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_code=${3:-200}

    printf "  %-25s" "$name..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "$expected_code" ]; then
        echo -e "${GREEN}OK${NC} (HTTP $HTTP_CODE)"
        return 0
    else
        echo -e "${RED}FAIL${NC} (HTTP $HTTP_CODE, expected $expected_code)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 1. Health Check
echo "1. Health Check"
echo "   ─────────────────────────────"
if check_endpoint "API Health" "/api/v1/health"; then
    # Show health details
    HEALTH=$(curl -s "$BASE_URL/api/v1/health" 2>/dev/null)
    if [ -n "$HEALTH" ]; then
        echo "   Response: $HEALTH"
    fi
fi
echo ""

# 2. Frontend
echo "2. Frontend"
echo "   ─────────────────────────────"
check_endpoint "Main page" "/"
echo ""

# 3. API Endpoints
echo "3. API Endpoints"
echo "   ─────────────────────────────"
check_endpoint "Dashboard summary" "/api/v1/dashboard/summary"
check_endpoint "Prospects list" "/api/v1/prospects"
check_endpoint "Campaigns list" "/api/v1/campaigns"
check_endpoint "Config" "/api/v1/config"
check_endpoint "Recent activity" "/api/v1/dashboard/activity"
echo ""

# 4. API Documentation
echo "4. Documentation"
echo "   ─────────────────────────────"
check_endpoint "Swagger UI" "/docs"
check_endpoint "ReDoc" "/redoc"
echo ""

# Summary
echo "=============================================="
if [ $FAILED -eq 0 ]; then
    echo -e "  ${GREEN}All checks passed!${NC}"
    echo ""
    echo "  Your deployment is ready at:"
    echo "  $BASE_URL"
else
    echo -e "  ${RED}$FAILED check(s) failed${NC}"
    echo ""
    echo "  Please review the failures above."
fi
echo "=============================================="

exit $FAILED
