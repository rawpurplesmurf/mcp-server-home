#!/usr/bin/env python3
"""
Test script to demonstrate MCP server configuration and usage.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
BASE_URL = f"http://localhost:{SERVER_PORT}"

def test_health():
    """Test the health endpoint."""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_tools_list():
    """Test the tools list endpoint."""
    print("🔧 Testing tools list...")
    response = requests.get(f"{BASE_URL}/v1/tools/list")
    print(f"Status: {response.status_code}")
    tools = response.json()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    print()

def test_network_time():
    """Test the network time tool."""
    print("🕐 Testing network time tool...")
    payload = {
        "tool_name": "get_network_time",
        "arguments": {},
        "session_id": "test-session"
    }
    response = requests.post(f"{BASE_URL}/v1/tools/call", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Time: {result['result_data']['readable_time']}")
    print(f"Source: {result['result_data']['source']}")
    print()

def test_ping():
    """Test the ping tool."""
    print("🏓 Testing ping tool...")
    payload = {
        "tool_name": "ping_host",
        "arguments": {"hostname": "google.com"},
        "session_id": "test-session"
    }
    response = requests.post(f"{BASE_URL}/v1/tools/call", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Host: {result['result_data']['host']}")
    print(f"Status: {result['result_data']['status']}")
    print(f"Packet Loss: {result['result_data']['packet_loss_percent']}%")
    print()

def main():
    """Run all tests."""
    print("🚀 MCP Server Configuration Test")
    print("=" * 40)
    print(f"Server URL: {BASE_URL}")
    print(f"NTP Server: {os.getenv('NTP_SERVER', 'pool.ntp.org')}")
    print(f"Redis Host: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}")
    print()
    
    try:
        test_health()
        test_tools_list()
        test_network_time()
        test_ping()
        print("✅ All tests completed successfully!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Is it running?")
        print(f"Start the server with: uvicorn server:app --port {SERVER_PORT}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()