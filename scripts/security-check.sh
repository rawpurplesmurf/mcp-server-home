#!/bin/bash

###############################################################################
# Bandit Security Testing Script
# Scans Python code for common security issues
###############################################################################

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Bandit Security Scanner${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if bandit is installed
if ! command -v bandit &> /dev/null; then
    echo -e "${YELLOW}Bandit not found. Installing...${NC}"
    pip install bandit
    echo ""
fi

echo -e "${YELLOW}Scanning Python files for security issues...${NC}"
echo ""

# Run bandit with configuration
bandit -c .bandit -r server.py client.py -f txt

EXIT_CODE=$?

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ No security issues found!${NC}"
else
    echo -e "${YELLOW}⚠ Security issues detected. Review the output above.${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Hardcoded passwords/secrets"
    echo "  - SQL injection vulnerabilities"
    echo "  - Shell injection risks"
    echo "  - Insecure random number generation"
    echo "  - Weak cryptography"
    echo ""
    echo "To suppress false positives, add comments like:"
    echo "  # nosec B101"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

exit $EXIT_CODE
