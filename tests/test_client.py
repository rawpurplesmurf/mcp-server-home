"""
Tests for MCP Client endpoints and functionality.
"""
import pytest
from httpx import AsyncClient


class TestClientHealth:
    """Test client health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client: AsyncClient, client_url: str):
        """Test client health check returns OK."""
        response = await http_client.get(f"{client_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "mcp-client"
        assert "ollama" in data
        assert "mcp_server" in data
        assert "model" in data
    
    @pytest.mark.asyncio
    async def test_health_includes_model_info(
        self, 
        http_client: AsyncClient, 
        client_url: str
    ):
        """Test health check includes Ollama model information."""
        response = await http_client.get(f"{client_url}/health")
        data = response.json()
        
        assert isinstance(data["model"], str)
        assert len(data["model"]) > 0


class TestClientTools:
    """Test client tools endpoint."""
    
    @pytest.mark.asyncio
    async def test_tools_endpoint(self, http_client: AsyncClient, client_url: str):
        """Test tools listing from client."""
        response = await http_client.get(f"{client_url}/tools")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) >= 2
    
    @pytest.mark.asyncio
    async def test_tools_have_required_fields(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that tools have all required fields."""
        response = await http_client.get(f"{client_url}/tools")
        tools = response.json()
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool


class TestDirectToolTesting:
    """Test direct tool testing endpoint."""
    
    @pytest.mark.asyncio
    async def test_test_tool_get_network_time(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test direct tool call for network time."""
        payload = {
            "tool_name": "get_network_time",
            "arguments": {}
        }
        
        response = await http_client.post(
            f"{client_url}/test-tool",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "result_data" in data
    
    @pytest.mark.asyncio
    async def test_test_tool_ping(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test direct tool call for ping."""
        payload = {
            "tool_name": "ping_host",
            "arguments": {"hostname": "localhost"}
        }
        
        response = await http_client.post(
            f"{client_url}/test-tool",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "result_data" in data


class TestChatEndpoint:
    """Test chat endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_time_query(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test chat with time-related query."""
        payload = {
            "message": "What time is it?",
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0  # Ollama can be slow
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "tools_used" in data
        assert "session_id" in data
        assert "timestamp" in data
        
        # Time query should use get_network_time tool
        assert "get_network_time" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_chat_ping_query(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test chat with ping-related query."""
        payload = {
            "message": "Can you ping localhost?",
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "tools_used" in data
        
        # Ping query should use ping_host tool
        assert "ping_host" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_chat_general_query(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test chat with general conversational query."""
        payload = {
            "message": "Hello, how are you?",
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
    
    @pytest.mark.asyncio
    async def test_chat_session_id_returned(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test that chat returns the same session ID."""
        payload = {
            "message": "test message",
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        data = response.json()
        
        assert data["session_id"] == test_session_id




class TestChatInputValidation:
    """Test chat endpoint input validation."""
    
    @pytest.mark.asyncio
    async def test_chat_empty_message(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test chat with empty message."""
        payload = {
            "message": "",
            "session_id": "test"
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        
        # Should either reject or handle gracefully
        assert response.status_code in [200, 422]


class TestHomeAssistantShortcuts:
    """Test Home Assistant query shortcuts in client."""
    
    @pytest.mark.asyncio
    async def test_temperature_query_detection(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that temperature queries are detected and routed to HA tool."""
        payload = {
            "message": "What's the temperature in the living room?",
            "session_id": "test-ha"
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should either use ha_get_device_state or return error about HA not configured
        if "tools_used" in data and data["tools_used"]:
            assert "ha_get_device_state" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_light_control_detection(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that light control commands are detected."""
        payload = {
            "message": "Turn on the kitchen lights",
            "session_id": "test-ha"
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should either use ha_control_light or return error about HA not configured
        if "tools_used" in data and data["tools_used"]:
            assert "ha_control_light" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_specific_light_control_detection(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that specific light names are detected."""
        payload = {
            "message": "Turn off the kitchen above cabinet light",
            "session_id": "test-ha"
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use ha_control_light with name_filter
        if "tools_used" in data and data["tools_used"]:
            assert "ha_control_light" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_switch_control_detection(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that switch control commands are detected."""
        payload = {
            "message": "Turn off the coffee maker",
            "session_id": "test-ha"
        }
        
        response = await http_client.post(
            f"{client_url}/chat",
            json=payload,
            timeout=60.0
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should either use ha_control_switch or return error about HA not configured
        if "tools_used" in data and data["tools_used"]:
            assert "ha_control_switch" in data["tools_used"]
    
    @pytest.mark.asyncio
    async def test_ha_tools_in_client_list(
        self,
        http_client: AsyncClient,
        client_url: str
    ):
        """Test that HA tools appear in client tools list."""
        response = await http_client.get(f"{client_url}/tools")
        assert response.status_code == 200
        
        tools = response.json()
        tool_names = [tool["name"] for tool in tools]
        
        # Client should expose HA tools from server
        assert "ha_get_device_state" in tool_names
        assert "ha_control_light" in tool_names
        assert "ha_control_switch" in tool_names


class TestFeedbackSystem:
    """Test feedback system endpoints."""
    
    @pytest.mark.asyncio
    async def test_chat_includes_interaction_id(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test that chat responses include interaction_id for feedback."""
        response = await http_client.post(
            f"{client_url}/chat",
            json={"message": "What time is it?", "session_id": test_session_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "interaction_id" in data
        assert isinstance(data["interaction_id"], str)
        assert len(data["interaction_id"]) > 0
    
    @pytest.mark.asyncio
    async def test_chat_includes_debug_info(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test that chat responses include debug information."""
        response = await http_client.post(
            f"{client_url}/chat",
            json={"message": "What time is it?", "session_id": test_session_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "debug" in data
        assert isinstance(data["debug"], dict)
        assert "routing" in data["debug"]
        assert data["debug"]["routing"] in ["direct_shortcut", "llm_with_tools", "llm_only"]
    
    @pytest.mark.asyncio
    async def test_feedback_thumbs_up_without_redis(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test thumbs up feedback (may fail if Redis not available)."""
        # First, send a message to get an interaction_id
        chat_response = await http_client.post(
            f"{client_url}/chat",
            json={"message": "What time is it?", "session_id": test_session_id}
        )
        assert chat_response.status_code == 200
        
        chat_data = chat_response.json()
        interaction_id = chat_data.get("interaction_id")
        
        if not interaction_id:
            pytest.skip("No interaction_id returned (Redis may be disabled)")
        
        # Now submit thumbs up feedback
        feedback_response = await http_client.post(
            f"{client_url}/feedback",
            json={
                "interaction_id": interaction_id,
                "session_id": test_session_id,
                "feedback": "thumbs_up"
            }
        )
        
        # Should succeed if Redis is available, or return 503 if not
        assert feedback_response.status_code in [200, 503]
        
        if feedback_response.status_code == 200:
            feedback_data = feedback_response.json()
            assert feedback_data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_feedback_thumbs_down_without_redis(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test thumbs down feedback (may fail if Redis not available)."""
        # First, send a message to get an interaction_id
        chat_response = await http_client.post(
            f"{client_url}/chat",
            json={"message": "ping google.com", "session_id": test_session_id}
        )
        assert chat_response.status_code == 200
        
        chat_data = chat_response.json()
        interaction_id = chat_data.get("interaction_id")
        
        if not interaction_id:
            pytest.skip("No interaction_id returned (Redis may be disabled)")
        
        # Now submit thumbs down feedback
        feedback_response = await http_client.post(
            f"{client_url}/feedback",
            json={
                "interaction_id": interaction_id,
                "session_id": test_session_id,
                "feedback": "thumbs_down"
            }
        )
        
        # Should succeed if Redis is available, or return 503 if not
        assert feedback_response.status_code in [200, 503]
        
        if feedback_response.status_code == 200:
            feedback_data = feedback_response.json()
            assert feedback_data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_feedback_invalid_type(
        self,
        http_client: AsyncClient,
        client_url: str,
        test_session_id: str
    ):
        """Test that invalid feedback types are rejected."""
        feedback_response = await http_client.post(
            f"{client_url}/feedback",
            json={
                "interaction_id": "fake_id",
                "session_id": test_session_id,
                "feedback": "invalid_feedback"
            }
        )
        
        # Should return 400 for invalid feedback type or 503 if Redis unavailable
        assert feedback_response.status_code in [400, 503]


class TestRootEndpoint:
    """Test root endpoint."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, http_client: AsyncClient, client_url: str):
        """Test root endpoint returns service information."""
        response = await http_client.get(f"{client_url}/")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data
        
        # Check that main endpoints are listed
        endpoints = data["endpoints"]
        assert "chat" in endpoints
        assert "health" in endpoints
        assert "tools" in endpoints
        assert "feedback" in endpoints  # New feedback endpoint


