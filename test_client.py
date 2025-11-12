#!/usr/bin/env python3
"""
Test script for the MCP client with Ollama integration.
"""

import asyncio
import json
import httpx
from dotenv import load_dotenv
import os

# Load client environment
load_dotenv(".env.client")

CLIENT_PORT = int(os.getenv("CLIENT_PORT", "8001"))
CLIENT_URL = f"http://localhost:{CLIENT_PORT}"

async def test_client():
    """Test the MCP client endpoints."""
    async with httpx.AsyncClient() as client:
        print("🤖 Testing MCP Client with Ollama Integration")
        print("=" * 50)
        
        # Test health
        print("🏥 Health Check...")
        try:
            response = await client.get(f"{CLIENT_URL}/health")
            health_data = response.json()
            print(f"Status: {response.status_code}")
            print(f"Ollama: {health_data.get('ollama', 'unknown')}")
            print(f"MCP Server: {health_data.get('mcp_server', 'unknown')}")
            print(f"Model: {health_data.get('model', 'unknown')}")
            print()
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Test tools list
        print("🔧 Available Tools...")
        try:
            response = await client.get(f"{CLIENT_URL}/tools")
            tools = response.json()
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
            print()
        except Exception as e:
            print(f"❌ Tools list failed: {e}")
        
        # Test chat with time question
        print("🕐 Testing Time Question...")
        try:
            chat_payload = {
                "message": "What time is it right now?",
                "session_id": "test-session"
            }
            response = await client.post(f"{CLIENT_URL}/chat", json=chat_payload)
            chat_data = response.json()
            print(f"Status: {response.status_code}")
            print(f"Response: {chat_data.get('response', 'No response')}")
            print(f"Tools Used: {chat_data.get('tools_used', [])}")
            print()
        except Exception as e:
            print(f"❌ Time chat failed: {e}")
        
        # Test chat with ping question
        print("🏓 Testing Ping Question...")
        try:
            chat_payload = {
                "message": "Can you ping google.com to test connectivity?",
                "session_id": "test-session"
            }
            response = await client.post(f"{CLIENT_URL}/chat", json=chat_payload)
            chat_data = response.json()
            print(f"Status: {response.status_code}")
            print(f"Response: {chat_data.get('response', 'No response')}")
            print(f"Tools Used: {chat_data.get('tools_used', [])}")
            print()
        except Exception as e:
            print(f"❌ Ping chat failed: {e}")
        
        # Test general conversation
        print("💬 Testing General Chat...")
        try:
            chat_payload = {
                "message": "Hello! What can you help me with?",
                "session_id": "test-session"
            }
            response = await client.post(f"{CLIENT_URL}/chat", json=chat_payload)
            chat_data = response.json()
            print(f"Status: {response.status_code}")
            print(f"Response: {chat_data.get('response', 'No response')}")
            print(f"Tools Used: {chat_data.get('tools_used', [])}")
            print()
        except Exception as e:
            print(f"❌ General chat failed: {e}")

def main():
    """Main function to run tests."""
    print("🚀 Starting MCP Client Tests")
    print(f"Client URL: {CLIENT_URL}")
    print("Make sure both the MCP server and client are running!")
    print()
    
    try:
        asyncio.run(test_client())
        print("✅ All tests completed!")
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    main()