#!/bin/bash

###############################################################################
# Unified Test Runner for MCP Project
# Executes pytest tests (backend) and Playwright tests (UI) in sequence
###############################################################################

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
PYTEST_PASSED=false
PLAYWRIGHT_PASSED=false
BANDIT_PASSED=false

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  MCP Unified Test Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

###############################################################################
# 1. Install test dependencies if needed
###############################################################################
echo -e "${YELLOW}[1/5] Checking test dependencies...${NC}"

if ! pip show pytest > /dev/null 2>&1; then
    echo "Installing pytest dependencies..."
    pip install -r requirements-test.txt
else
    echo "✓ pytest dependencies already installed"
fi

echo ""

###############################################################################
# 2. Run bandit security tests
###############################################################################
echo -e "${YELLOW}[2/5] Running bandit security tests...${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

# Run bandit security linter
if bandit -c .bandit -r server.py client.py -f txt; then
    echo -e "${GREEN}✓ bandit security tests passed (no issues found)${NC}"
    BANDIT_PASSED=true
else
    echo -e "${YELLOW}⚠ bandit found potential security issues${NC}"
    echo "Review the output above for details."
    BANDIT_PASSED=false
fi

echo ""

###############################################################################
# 3. Run pytest tests (backend)
###############################################################################
echo -e "${YELLOW}[3/5] Running pytest tests (backend)...${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

# Check if services are running
SERVER_RUNNING=$(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "true" || echo "false")
CLIENT_RUNNING=$(curl -s http://localhost:8001/health > /dev/null 2>&1 && echo "true" || echo "false")

if [ "$SERVER_RUNNING" = "false" ] || [ "$CLIENT_RUNNING" = "false" ]; then
    echo -e "${RED}⚠ Warning: Services not running.${NC}"
    echo "Please ensure both server (port 8000) and client (port 8001) are running."
    echo "You can start them with: npm start  or  bash scripts/start.sh"
    echo ""
fi

# Run pytest with coverage
if pytest tests/ --cov=. --cov-report=term-missing --cov-report=html -v; then
    echo -e "${GREEN}✓ pytest tests passed${NC}"
    PYTEST_PASSED=true
else
    echo -e "${RED}✗ pytest tests failed${NC}"
    PYTEST_PASSED=false
fi

echo ""

###############################################################################
# 4. Run Playwright tests (UI)
###############################################################################
echo -e "${YELLOW}[4/5] Running Playwright tests (UI)...${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

# Check if UI dependencies are installed
cd ui
if [ ! -d "node_modules" ] || [ ! -d "node_modules/@playwright" ]; then
    echo "Installing UI test dependencies..."
    npm install
    npx playwright install chromium
fi

# Run Playwright tests
if npx playwright test; then
    echo -e "${GREEN}✓ Playwright tests passed${NC}"
    PLAYWRIGHT_PASSED=true
else
    echo -e "${RED}✗ Playwright tests failed${NC}"
    PLAYWRIGHT_PASSED=false
fi

cd ..
echo ""

###############################################################################
# 5. Summary
###############################################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Test Results Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$BANDIT_PASSED" = "true" ]; then
    echo -e "  Security (bandit):   ${GREEN}✓ PASSED${NC}"
else
    echo -e "  Security (bandit):   ${YELLOW}⚠ WARNINGS${NC}"
fi

if [ "$PYTEST_PASSED" = "true" ]; then
    echo -e "  Backend (pytest):    ${GREEN}✓ PASSED${NC}"
else
    echo -e "  Backend (pytest):    ${RED}✗ FAILED${NC}"
fi

if [ "$PLAYWRIGHT_PASSED" = "true" ]; then
    echo -e "  Frontend (Playwright): ${GREEN}✓ PASSED${NC}"
else
    echo -e "  Frontend (Playwright): ${RED}✗ FAILED${NC}"
fi

echo ""

if [ "$PYTEST_PASSED" = "true" ] && [ "$PLAYWRIGHT_PASSED" = "true" ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ALL TESTS PASSED ✓                                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    
    if [ "$BANDIT_PASSED" = "false" ]; then
        echo -e "${YELLOW}Note: Security warnings found. Review bandit output above.${NC}"
    fi
    
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  SOME TESTS FAILED ✗                                      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
