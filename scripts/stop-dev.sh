#!/bin/bash

# Stop all development services
# Run with: bash scripts/stop-dev.sh

echo "🛑 Stopping development services..."

# Kill by PID files if they exist
if [ -f "logs/dev_server.pid" ]; then
    kill $(cat logs/dev_server.pid) 2>/dev/null && echo "  ✓ Stopped MCP Server"
    rm -f logs/dev_server.pid
fi

if [ -f "logs/dev_client.pid" ]; then
    kill $(cat logs/dev_client.pid) 2>/dev/null && echo "  ✓ Stopped MCP Client"
    rm -f logs/dev_client.pid
fi

if [ -f "logs/dev_ui.pid" ]; then
    kill $(cat logs/dev_ui.pid) 2>/dev/null && echo "  ✓ Stopped Web UI"
    rm -f logs/dev_ui.pid
fi

# Also kill by port as backup
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "✅ All services stopped."
