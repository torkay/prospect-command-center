#!/bin/bash
set -e

echo "Setting up Prospect Scraper..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"
echo "Dependencies installed"

# Install Playwright browser
playwright install chromium
echo "Playwright browser installed"

# Copy env file if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file (edit with your API keys)"
fi

# Run tests
echo ""
echo "Running tests..."
pytest tests/ -v --tb=short -x || true

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your SERPAPI_KEY"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: prospect --help"
echo "  4. Or:  make run  (start web UI)"
