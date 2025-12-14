#!/bin/bash
#
# Prospect Scraper Beta Setup
# One command to get testing:
# curl -sSL https://raw.githubusercontent.com/torkay/prospect-scraper/beta/scripts/beta-setup.sh | bash
#

set -e

REPO="https://github.com/torkay/prospect-scraper.git"
BRANCH="beta"
DIR="prospect-scraper-beta"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "       PROSPECT SCRAPER - BETA TESTING SETUP                "
echo "============================================================"
echo ""

# Check Prerequisites
echo "Checking prerequisites..."

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "  ${GREEN}OK${NC} Python $PYTHON_VERSION"
    else
        echo -e "  ${RED}ERROR${NC} Python 3.10+ required (found $PYTHON_VERSION)"
        echo "    Install: https://www.python.org/downloads/"
        exit 1
    fi
else
    echo -e "  ${RED}ERROR${NC} Python not found"
    echo "    Install: https://www.python.org/downloads/"
    exit 1
fi

# Git
if command -v git &> /dev/null; then
    echo -e "  ${GREEN}OK${NC} Git $(git --version | cut -d' ' -f3)"
else
    echo -e "  ${RED}ERROR${NC} Git not found"
    echo "    Install: https://git-scm.com/downloads"
    exit 1
fi

# Clone Repository
echo ""
echo "Cloning repository..."

if [ -d "$DIR" ]; then
    echo -e "  ${YELLOW}!${NC} Directory exists, pulling latest..."
    cd "$DIR"
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
else
    git clone -b $BRANCH "$REPO" "$DIR"
    cd "$DIR"
fi

echo -e "  ${GREEN}OK${NC} Repository ready"

# Setup Virtual Environment
echo ""
echo "Setting up virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate (cross-platform)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

echo -e "  ${GREEN}OK${NC} Virtual environment active"

# Install Dependencies
echo ""
echo "Installing dependencies..."

pip install --upgrade pip -q
pip install -e ".[dev]" -q

echo -e "  ${GREEN}OK${NC} Python dependencies installed"

# Install Playwright browser
echo "Installing browser (this may take a minute)..."
playwright install chromium 2>/dev/null || playwright install chromium

echo -e "  ${GREEN}OK${NC} Playwright browser installed"

# Environment Configuration
echo ""
echo "Configuring environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${YELLOW}!${NC} Created .env file"
else
    echo -e "  ${GREEN}OK${NC} .env file exists"
fi

# Run Tests
echo ""
echo "Running test suite..."

pytest tests/ -v --tb=line -q 2>&1 | tail -20

# Summary
echo ""
echo "============================================================"
echo "                    SETUP COMPLETE                          "
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Add your SerpAPI key:"
echo "     ${YELLOW}echo 'SERPAPI_KEY=your_key_here' >> .env${NC}"
echo ""
echo "  2. Activate the virtual environment:"
echo "     ${YELLOW}source venv/bin/activate${NC}  (or venv\\Scripts\\activate on Windows)"
echo ""
echo "  3. Run the CLI:"
echo "     ${YELLOW}prospect search \"plumber\" \"Sydney\" --limit 5${NC}"
echo ""
echo "  4. Or start the web UI:"
echo "     ${YELLOW}make run${NC}"
echo "     Open: http://localhost:8000"
echo ""
echo "  5. Run tests:"
echo "     ${YELLOW}make test${NC}"
echo ""
echo "Report issues: https://github.com/torkay/prospect-scraper/issues"
echo ""
