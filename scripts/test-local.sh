#!/bin/bash
set -e

echo "Running local test suite..."

# Activate venv if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run unit tests
echo ""
echo "=== Unit Tests ==="
pytest tests/ -v --tb=short -m "not integration"

# Run integration tests if API key present
if [ -n "$SERPAPI_KEY" ]; then
    echo ""
    echo "=== Integration Tests ==="
    pytest tests/ -v --tb=short -m integration || true
else
    echo ""
    echo "Skipping integration tests (SERPAPI_KEY not set)"
fi

# Lint
echo ""
echo "=== Linting ==="
ruff check prospect/ tests/ || true

echo ""
echo "Tests complete!"
