#!/bin/bash

# Development script - starts all three services with logging
# Run with: bash scripts/dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════"
echo "  Starting MCP Development Environment"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run 'bash scripts/setup.sh' first."
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping &> /dev/null; then
    echo "⚠️  Warning: Redis is not running. Interaction logging will be disabled."
    echo "   To enable logging, start Redis: brew services start redis"
    echo ""
fi

# Create logs directory
mkdir -p logs

# Kill any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
sleep 1

echo ""
echo "🚀 Starting services..."
echo ""

# Start MCP Server (port 8000)
echo "📡 Starting MCP Server on port 8000..."
.venv/bin/uvicorn server:app --reload --port 8000 > logs/dev_server.log 2>&1 &
SERVER_PID=$!
echo "   PID: $SERVER_PID"

# Wait for server to be ready
sleep 2

# Start MCP Client (port 8001)
echo "🤖 Starting MCP Client on port 8001..."
.venv/bin/uvicorn client:app --reload --port 8001 > logs/dev_client.log 2>&1 &
CLIENT_PID=$!
echo "   PID: $CLIENT_PID"

# Wait for client to be ready
sleep 2

# Start UI (port 5173)
echo "🌐 Starting Web UI on port 5173..."
cd ui && npm run dev > ../logs/dev_ui.log 2>&1 &
UI_PID=$!
echo "   PID: $UI_PID"
cd ..

sleep 3

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ All services started!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  📡 MCP Server:  http://localhost:8000"
echo "  🤖 MCP Client:  http://localhost:8001"
echo "  🌐 Web UI:      http://localhost:5173"
echo ""
echo "  📝 Logs:"
echo "     Server:  tail -f logs/dev_server.log"
echo "     Client:  tail -f logs/dev_client.log"
echo "     UI:      tail -f logs/dev_ui.log"
echo ""
echo "  🛑 To stop all services: bash scripts/stop-dev.sh"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# Save PIDs for stop script
echo "$SERVER_PID" > logs/dev_server.pid
echo "$CLIENT_PID" > logs/dev_client.pid
echo "$UI_PID" > logs/dev_ui.pid

echo "Press Ctrl+C to stop all services..."
echo ""

# Trap Ctrl+C and cleanup
trap 'echo ""; echo "🛑 Stopping all services..."; kill $SERVER_PID $CLIENT_PID $UI_PID 2>/dev/null; rm -f logs/dev_*.pid; echo "✅ All services stopped."; exit 0' INT TERM

# Keep script running and show combined logs
tail -f logs/dev_server.log -f logs/dev_client.log -f logs/dev_ui.log
