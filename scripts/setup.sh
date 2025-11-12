#!/usr/bin/env bash

###############################################################################
# MCP Project Setup Script
# Sets up Python virtual environment, installs all dependencies,
# and configures Playwright for testing
###############################################################################

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          MCP Project Environment Setup                        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# 1. Check Prerequisites
###############################################################################
echo -e "${CYAN}[1/6] Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3.10 or higher${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed${NC}"
    echo -e "${YELLOW}Please install Node.js 18 or higher${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm is not installed${NC}"
    echo -e "${YELLOW}Please install npm${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}✓ npm ${NPM_VERSION} found${NC}"

echo ""

###############################################################################
# 2. Setup Python Virtual Environment
###############################################################################
echo -e "${CYAN}[2/6] Setting up Python virtual environment...${NC}"

if [ -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf .venv
        python3 -m venv .venv
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    else
        echo -e "${GREEN}✓ Using existing virtual environment${NC}"
    fi
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

###############################################################################
# 3. Install Python Dependencies
###############################################################################
echo -e "${CYAN}[3/6] Installing Python dependencies...${NC}"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1

# Install production dependencies
echo -e "${YELLOW}Installing production dependencies...${NC}"
pip install -r requirements.txt

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -r requirements-test.txt

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

###############################################################################
# 4. Install Node.js Dependencies
###############################################################################
echo -e "${CYAN}[4/6] Installing Node.js dependencies...${NC}"

# Install root dependencies
echo -e "${YELLOW}Installing root npm dependencies...${NC}"
npm install

# Install UI dependencies
echo -e "${YELLOW}Installing UI dependencies...${NC}"
cd ui
npm install
cd ..

echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
echo ""

###############################################################################
# 5. Setup Playwright
###############################################################################
echo -e "${CYAN}[5/6] Setting up Playwright...${NC}"

echo -e "${YELLOW}Installing Playwright browsers (Chromium)...${NC}"
cd ui
npx playwright install chromium
cd ..

echo -e "${GREEN}✓ Playwright configured${NC}"
echo ""

###############################################################################
# 6. Setup Environment Files
###############################################################################
echo -e "${CYAN}[6/6] Setting up environment files...${NC}"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Create .env.client if it doesn't exist
if [ ! -f ".env.client" ]; then
    echo -e "${YELLOW}Creating .env.client from template...${NC}"
    cp .env.client.example .env.client
    echo -e "${GREEN}✓ .env.client created${NC}"
else
    echo -e "${GREEN}✓ .env.client already exists${NC}"
fi

echo ""

###############################################################################
# Summary
###############################################################################
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               Setup Complete! ✓                                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Your MCP project environment is ready!${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo ""
echo -e "  ${YELLOW}1. Activate the virtual environment:${NC}"
echo -e "     ${CYAN}source .venv/bin/activate${NC}"
echo ""
echo -e "  ${YELLOW}2. (Optional) Install Ollama and pull the model:${NC}"
echo -e "     ${CYAN}ollama pull qwen2.5:7b-instruct${NC}"
echo ""
echo -e "  ${YELLOW}3. (Optional) Install and start Redis:${NC}"
echo -e "     ${CYAN}# macOS: brew install redis && brew services start redis${NC}"
echo -e "     ${CYAN}# Linux: sudo apt install redis-server && sudo systemctl start redis${NC}"
echo ""
echo -e "  ${YELLOW}4. Configure environment files:${NC}"
echo -e "     ${CYAN}Edit .env and .env.client with your settings${NC}"
echo ""
echo -e "  ${YELLOW}5. Start all services:${NC}"
echo -e "     ${CYAN}npm start${NC}"
echo -e "     ${CYAN}# Or: bash scripts/start.sh${NC}"
echo ""
echo -e "  ${YELLOW}6. Run tests:${NC}"
echo -e "     ${CYAN}npm test${NC}"
echo -e "     ${CYAN}# Or: bash scripts/run-tests.sh${NC}"
echo ""
echo -e "${GREEN}For more information, see:${NC}"
echo -e "  ${CYAN}• README.md - General documentation${NC}"
echo -e "  ${CYAN}• docs/MACOS_DEV.md - macOS setup guide${NC}"
echo -e "  ${CYAN}• docs/LINUX_DEV.md - Linux setup guide${NC}"
echo -e "  ${CYAN}• docs/WINDOWS_DEV.md - Windows setup guide${NC}"
echo ""
