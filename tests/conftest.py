"""
Pytest configuration and fixtures for MCP tests.
"""
import asyncio
import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def server_url() -> str:
    """MCP Server URL."""
    return "http://localhost:8000"


@pytest.fixture
def client_url() -> str:
    """MCP Client URL."""
    return "http://localhost:8001"


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for making requests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def test_session_id() -> str:
    """Test session ID."""
    return "test-session-pytest"
