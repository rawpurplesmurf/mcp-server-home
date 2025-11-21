#!/usr/bin/env bash

# Start script for MCP Server, Client, and Web UI
# Runs all services with auto-reload and logs output to separate files
# Kills all services when this script is terminated

set -e

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
NC='\033[0m' # No Color

# Log directory
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Log files with timestamps
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SERVER_LOG="$LOG_DIR/server_$TIMESTAMP.log"
CLIENT_LOG="$LOG_DIR/client_$TIMESTAMP.log"
UI_LOG="$LOG_DIR/ui_$TIMESTAMP.log"

# PID tracking
SERVER_PID=""
CLIENT_PID=""
UI_PID=""

# Cleanup function to kill all services
cleanup() {
    echo -e "\n${YELLOW}Shutting down all services...${NC}"
    
    if [ ! -z "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping MCP Server (PID: $SERVER_PID)${NC}"
        kill -TERM $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$CLIENT_PID" ] && kill -0 $CLIENT_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping MCP Client (PID: $CLIENT_PID)${NC}"
        kill -TERM $CLIENT_PID 2>/dev/null || true
        wait $CLIENT_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$UI_PID" ] && kill -0 $UI_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping Web UI (PID: $UI_PID)${NC}"
        kill -TERM $UI_PID 2>/dev/null || true
        wait $UI_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Set up trap to catch SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Starting MCP Server, Client, and Web UI          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Logs will be written to:${NC}"
echo -e "  Server: ${SERVER_LOG}"
echo -e "  Client: ${CLIENT_LOG}"
echo -e "  UI:     ${UI_LOG}"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo -e "${YELLOW}Consider activating your venv first: source .venv/bin/activate${NC}"
    echo ""
fi

# Start MCP Server (port 8000) with auto-reload
echo -e "${GREEN}[1/3] Starting MCP Server on port 8000...${NC}"
uvicorn server:app --reload --host 0.0.0.0 --port 8000 > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
echo -e "  PID: $SERVER_PID"

# Wait a moment for server to start
sleep 2

# Check if server is still running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}Failed to start MCP Server${NC}"
    echo -e "${RED}Check logs: $SERVER_LOG${NC}"
    exit 1
fi

# Start MCP Client (port 8001) with auto-reload
echo -e "${GREEN}[2/3] Starting MCP Client on port 8001...${NC}"
uvicorn client:app --reload --host 0.0.0.0 --port 8001 > "$CLIENT_LOG" 2>&1 &
CLIENT_PID=$!
echo -e "  PID: $CLIENT_PID"

# Wait a moment for client to start
sleep 2

# Check if client is still running
if ! kill -0 $CLIENT_PID 2>/dev/null; then
    echo -e "${RED}Failed to start MCP Client${NC}"
    echo -e "${RED}Check logs: $CLIENT_LOG${NC}"
    cleanup
    exit 1
fi

# Start Web UI (port 5173)
echo -e "${GREEN}[3/3] Starting Web UI on port 5173...${NC}"
if [ ! -d "ui/node_modules" ]; then
    echo -e "${YELLOW}  Installing UI dependencies (first time)...${NC}"
    cd ui && npm install > "../$UI_LOG" 2>&1 && cd ..
fi

cd ui && npm run dev > "../$UI_LOG" 2>&1 &
UI_PID=$!
cd ..
echo -e "  PID: $UI_PID"

# Wait a moment for UI to start
sleep 3

# Check if UI is still running
if ! kill -0 $UI_PID 2>/dev/null; then
    echo -e "${RED}Failed to start Web UI${NC}"
    echo -e "${RED}Check logs: $UI_LOG${NC}"
    cleanup
    exit 1
fi

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
echo -e "${YELLOW}View logs in real-time:${NC}"
echo -e "  tail -f $SERVER_LOG"
echo -e "  tail -f $CLIENT_LOG"
echo -e "  tail -f $UI_LOG"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all processes (this will block until they exit or are killed)
wait $SERVER_PID $CLIENT_PID $UI_PID

