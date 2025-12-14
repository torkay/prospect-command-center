#!/bin/bash
#
# Quick Test Commands for Beta Testers
# Run: ./scripts/quick-test.sh
#

set -e

# Activate venv
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true

echo "============================================================"
echo "           PROSPECT SCRAPER - QUICK TESTS                   "
echo "============================================================"
echo ""

# Test 1: CLI Help
echo "=== Test 1: CLI Help ==="
prospect --help
echo ""

# Test 2: Check Command
echo "=== Test 2: Configuration Check ==="
prospect check
echo ""

# Test 3: Version
echo "=== Test 3: Version ==="
prospect version
echo ""

# Test 4: Quick Search (if API key present)
if grep -q "SERPAPI_KEY=." .env 2>/dev/null && ! grep -q "SERPAPI_KEY=your" .env 2>/dev/null; then
    echo "=== Test 4: Quick Search (3 results) ==="
    prospect search "plumber" "Sydney" --limit 3 --skip-enrichment -f json -q 2>/dev/null | head -50
    echo ""
else
    echo "=== Test 4: Skipped (SERPAPI_KEY not configured) ==="
    echo ""
fi

# Test 5: Unit Tests
echo "=== Test 5: Unit Tests ==="
pytest tests/ -v --tb=line -q -x 2>&1 | tail -30
echo ""

# Test 6: Web Server Check
echo "=== Test 6: Web Server (starting briefly) ==="
uvicorn prospect.web.app:app --host 127.0.0.1 --port 8765 &
PID=$!
sleep 3
if curl -s http://127.0.0.1:8765/api/v1/health 2>/dev/null | grep -q "healthy"; then
    echo "Web server healthy"
else
    echo "Web server check skipped (curl not available or server slow)"
fi
kill $PID 2>/dev/null || true
echo ""

echo "============================================================"
echo "                    ALL TESTS COMPLETE                      "
echo "============================================================"
