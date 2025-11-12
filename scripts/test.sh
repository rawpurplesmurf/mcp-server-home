#!/usr/bin/env bash

# Test script for MCP Server and Client
# Tests all endpoints and tools

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Server URLs
SERVER_URL="http://localhost:8000"
CLIENT_URL="http://localhost:8001"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_test() {
    echo -e "\n${YELLOW}Testing:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    local expected=$5
    
    print_test "$name"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if [ -z "$expected" ] || echo "$body" | grep -q "$expected"; then
            print_success "$name (HTTP $http_code)"
            echo "Response: $body" | head -c 200
            [ ${#body} -gt 200 ] && echo "..." || echo ""
        else
            print_fail "$name - Expected text not found: $expected"
            echo "Response: $body"
        fi
    else
        print_fail "$name (HTTP $http_code)"
        echo "Response: $body"
    fi
}

# Start testing
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║       MCP Server & Client Test Suite                 ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if servers are running
print_header "Checking Server Availability"

if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: MCP Server is not running on $SERVER_URL${NC}"
    echo "Start it with: uvicorn server:app --port 8000"
    exit 1
fi
echo -e "${GREEN}✓ MCP Server is running${NC}"

if ! curl -s "$CLIENT_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: MCP Client is not running on $CLIENT_URL${NC}"
    echo "Start it with: uvicorn client:app --port 8001"
    exit 1
fi
echo -e "${GREEN}✓ MCP Client is running${NC}"

# MCP Server Tests
print_header "MCP Server Tests (Port 8000)"

test_endpoint \
    "Server Health Check" \
    "GET" \
    "$SERVER_URL/health" \
    "" \
    "ok"

test_endpoint \
    "List Available Tools" \
    "GET" \
    "$SERVER_URL/v1/tools/list" \
    "" \
    "get_network_time"

test_endpoint \
    "Call get_network_time Tool" \
    "POST" \
    "$SERVER_URL/v1/tools/call" \
    '{"tool_name": "get_network_time", "arguments": {}, "session_id": "test"}' \
    "timestamp_utc"

test_endpoint \
    "Call ping_host Tool (google.com)" \
    "POST" \
    "$SERVER_URL/v1/tools/call" \
    '{"tool_name": "ping_host", "arguments": {"hostname": "google.com"}, "session_id": "test"}' \
    "host"

test_endpoint \
    "Call ping_host Tool (localhost)" \
    "POST" \
    "$SERVER_URL/v1/tools/call" \
    '{"tool_name": "ping_host", "arguments": {"hostname": "localhost"}, "session_id": "test"}' \
    "host"

test_endpoint \
    "LLM Generate with Time Query" \
    "POST" \
    "$SERVER_URL/v1/generate" \
    '{"session_id": "test", "prompt": "What time is it?"}' \
    "time"

# MCP Client Tests
print_header "MCP Client Tests (Port 8001)"

test_endpoint \
    "Client Health Check" \
    "GET" \
    "$CLIENT_URL/health" \
    "" \
    "ok"

test_endpoint \
    "Client List Tools" \
    "GET" \
    "$CLIENT_URL/tools" \
    "" \
    "get_network_time"

test_endpoint \
    "Chat - Time Question" \
    "POST" \
    "$CLIENT_URL/chat" \
    '{"message": "What time is it?", "session_id": "test-session"}' \
    "time"

test_endpoint \
    "Chat - Ping Question" \
    "POST" \
    "$CLIENT_URL/chat" \
    '{"message": "Can you ping google.com?", "session_id": "test-session"}' \
    "ping"

test_endpoint \
    "Chat - General Question" \
    "POST" \
    "$CLIENT_URL/chat" \
    '{"message": "Hello, what can you do?", "session_id": "test-session"}' \
    "response"

test_endpoint \
    "Direct Tool Test - get_network_time" \
    "POST" \
    "$CLIENT_URL/test-tool" \
    '{"tool_name": "get_network_time", "arguments": {}}' \
    "status"

test_endpoint \
    "Direct Tool Test - ping_host" \
    "POST" \
    "$CLIENT_URL/test-tool" \
    '{"tool_name": "ping_host", "arguments": {"hostname": "1.1.1.1"}}' \
    "status"

# Error handling tests
print_header "Error Handling Tests"

test_endpoint \
    "Invalid Tool Name" \
    "POST" \
    "$SERVER_URL/v1/tools/call" \
    '{"tool_name": "nonexistent_tool", "arguments": {}, "session_id": "test"}' \
    "error"

test_endpoint \
    "Missing Required Argument" \
    "POST" \
    "$SERVER_URL/v1/tools/call" \
    '{"tool_name": "ping_host", "arguments": {}, "session_id": "test"}' \
    "error"

# Summary
print_header "Test Summary"

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo ""
echo -e "Total Tests: ${BLUE}$TOTAL${NC}"
echo -e "Passed:      ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed:      ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ALL TESTS PASSED! ✓                         ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           SOME TESTS FAILED ✗                         ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
