#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        MCP Server + Client + UI Docker Container      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Create .env files if they don't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
fi

if [ ! -f .env.client ]; then
    echo -e "${YELLOW}Creating .env.client from template...${NC}"
    cp .env.client.example .env.client
fi

# Function to start service in background
start_service() {
    local name=$1
    local command=$2
    local port=$3
    
    echo -e "${GREEN}Starting $name on port $port...${NC}"
    $command &
    local pid=$!
    
    # Wait for service to be ready
    sleep 3
    if ! kill -0 $pid 2>/dev/null; then
        echo -e "${RED}Failed to start $name${NC}"
        exit 1
    fi
    
    echo -e "  ✓ $name running (PID: $pid)"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down all services...${NC}"
    pkill -f "uvicorn" || true
    pkill -f "python3 -m http.server" || true
    exit 0
}

# Set up trap to catch SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start MCP Server
start_service "MCP Server" "uvicorn server:app --host 0.0.0.0 --port 8000" "8000"

# Start MCP Client  
start_service "MCP Client" "uvicorn client:app --host 0.0.0.0 --port 8001" "8001"

# Start static file server for UI
echo -e "${GREEN}Starting Web UI on port 5173...${NC}"
python3 -m http.server 5173 --directory ui/dist --bind 0.0.0.0 &
UI_PID=$!
sleep 2
if ! kill -0 $UI_PID 2>/dev/null; then
    echo -e "${RED}Failed to start Web UI${NC}"
    exit 1
fi
echo -e "  ✓ Web UI running (PID: $UI_PID)"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ ALL SERVICES RUNNING                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Access the services:${NC}"
echo -e "  ${YELLOW}🌐 Web UI:${NC}      http://localhost:5173"
echo -e "  ${YELLOW}🤖 MCP Client:${NC}  http://localhost:8001"
echo -e "  ${YELLOW}🖥️  MCP Server:${NC}  http://localhost:8000"
echo ""
echo -e "${GREEN}Container is ready! Press Ctrl+C to stop.${NC}"

# Wait for all background processes
wait