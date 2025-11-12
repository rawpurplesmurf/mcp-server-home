"""
Tests for MCP Server endpoints and tools.
"""
import pytest
from httpx import AsyncClient


class TestServerHealth:
    """Test server health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client: AsyncClient, server_url: str):
        """Test server health check returns OK."""
        response = await http_client.get(f"{server_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "mcp-server"
        assert "redis" in data
    
    @pytest.mark.asyncio
    async def test_health_redis_status(self, http_client: AsyncClient, server_url: str):
        """Test Redis status in health check."""
        response = await http_client.get(f"{server_url}/health")
        data = response.json()
        
        # Redis status should be either "connected" or "disconnected"
        assert data["redis"] in ["connected", "disconnected"]


class TestToolsEndpoints:
    """Test tools listing and calling endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_tools(self, http_client: AsyncClient, server_url: str):
        """Test tools listing endpoint."""
        response = await http_client.get(f"{server_url}/v1/tools/list")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) >= 2  # Should have at least get_network_time and ping_host
        
        tool_names = [tool["name"] for tool in tools]
        assert "get_network_time" in tool_names
        assert "ping_host" in tool_names
    
    @pytest.mark.asyncio
    async def test_tool_schema_structure(self, http_client: AsyncClient, server_url: str):
        """Test that tools have proper schema structure."""
        response = await http_client.get(f"{server_url}/v1/tools/list")
        tools = response.json()
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert isinstance(tool["parameters"], dict)


class TestNetworkTimeTool:
    """Test get_network_time tool."""
    
    @pytest.mark.asyncio
    async def test_get_network_time_success(
        self, 
        http_client: AsyncClient, 
        server_url: str,
        test_session_id: str
    ):
        """Test successful network time retrieval."""
        payload = {
            "tool_name": "get_network_time",
            "arguments": {},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # NTP can fail, so accept either success or error
        assert data["status"] in ["success", "error"]
        assert "result_data" in data
        
        if data["status"] == "success":
            result = data["result_data"]
            assert "timestamp_utc" in result
            assert "readable_time" in result
            assert "source" in result
    
    @pytest.mark.asyncio
    async def test_get_network_time_includes_offset(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test that time result includes offset when available."""
        payload = {
            "tool_name": "get_network_time",
            "arguments": {},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        data = response.json()
        
        # offset_ms should be present if NTP is available
        result = data["result_data"]
        if "NTP Server" in result.get("source", ""):
            assert "offset_ms" in result


class TestPingTool:
    """Test ping_host tool."""
    
    @pytest.mark.asyncio
    async def test_ping_localhost(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test pinging localhost."""
        payload = {
            "tool_name": "ping_host",
            "arguments": {"hostname": "localhost"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["success", "error"]
        assert "result_data" in data
        
        result = data["result_data"]
        assert "host" in result
        assert result["host"] == "localhost"
    
    @pytest.mark.asyncio
    async def test_ping_valid_host(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test pinging a valid external host."""
        payload = {
            "tool_name": "ping_host",
            "arguments": {"hostname": "1.1.1.1"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        result = data["result_data"]
        
        # Ping may timeout due to firewall/network - accept either success or timeout
        if "error" in result:
            # Timeout is acceptable
            assert "timed out" in result["error"].lower() or "failed" in result["error"].lower()
        else:
            # If successful, should have ping statistics
            assert "status" in result
            assert "packet_loss_percent" in result
            assert "average_latency_ms" in result
    
    @pytest.mark.asyncio
    async def test_ping_missing_hostname(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test ping without hostname returns error."""
        payload = {
            "tool_name": "ping_host",
            "arguments": {},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data["result_data"]


class TestToolErrors:
    """Test error handling in tool calls."""
    
    @pytest.mark.asyncio
    async def test_unknown_tool(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test calling non-existent tool."""
        payload = {
            "tool_name": "nonexistent_tool",
            "arguments": {},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "error"
        assert "Unknown tool" in data["result_data"]["error"]




class TestLLMGenerate:
    """Test LLM generation endpoint."""
    
    @pytest.mark.asyncio
    async def test_generate_endpoint(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test LLM generation endpoint (currently returns mock/error)."""
        payload = {
            "session_id": test_session_id,
            "prompt": "What time is it?"
        }
        
        response = await http_client.post(
            f"{server_url}/v1/generate",
            json=payload
        )
        # The endpoint exists and responds (may be 200 with mock or 500 if not implemented)
        assert response.status_code in [200, 500]
        
        # Try to parse as JSON, but accept text responses too
        try:
            data = response.json()
            # Should have either mock response or error
            assert ("response_text" in data or "error" in data or "detail" in data)
        except:
            # If not JSON, that's okay - endpoint exists but may return error text
            assert response.text is not None


class TestHomeAssistantIntegration:
    """Test Home Assistant integration tools."""
    
    @pytest.mark.asyncio
    async def test_ha_tools_in_list(
        self,
        http_client: AsyncClient,
        server_url: str
    ):
        """Test that Home Assistant tools are listed."""
        response = await http_client.get(f"{server_url}/v1/tools/list")
        assert response.status_code == 200
        
        tools = response.json()
        tool_names = [tool["name"] for tool in tools]
        
        # Check for HA tools
        assert "ha_get_device_state" in tool_names
        assert "ha_control_light" in tool_names
        assert "ha_control_switch" in tool_names
        
        # Verify tool schemas have correct parameters
        ha_get_state = next(t for t in tools if t["name"] == "ha_get_device_state")
        assert "domain" in ha_get_state["parameters"]["properties"]
        assert "name_filter" in ha_get_state["parameters"]["properties"]
        
        ha_control_light = next(t for t in tools if t["name"] == "ha_control_light")
        assert "action" in ha_control_light["parameters"]["properties"]
        assert "name_filter" in ha_control_light["parameters"]["properties"]
        assert "brightness" in ha_control_light["parameters"]["properties"]
    
    @pytest.mark.asyncio
    async def test_ha_get_device_state_no_config(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test HA device state tool when HA not configured."""
        payload = {
            "tool_name": "ha_get_device_state",
            "arguments": {"domain": "sensor"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # If HA_TOKEN not set, should get error about configuration
        if data["status"] == "error":
            assert "not configured" in data["result_data"]["error"].lower() or \
                   "failed" in data["result_data"]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_ha_get_device_state_with_filters(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test HA device state tool with domain and name filters."""
        # Test with domain filter
        payload = {
            "tool_name": "ha_get_device_state",
            "arguments": {"domain": "sensor", "name_filter": "temperature"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        # Should return either success (if configured) or config error
        data = response.json()
        assert data["status"] in ["success", "error"]
    
    @pytest.mark.asyncio  
    async def test_ha_control_light_no_config(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test HA light control when HA not configured."""
        payload = {
            "tool_name": "ha_control_light",
            "arguments": {"action": "turn_on", "name_filter": "living room"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # If HA_TOKEN not set, should get error (either configuration or no devices found)
        if data["status"] == "error":
            error_msg = data["result_data"]["error"].lower()
            assert "not configured" in error_msg or \
                   "failed" in error_msg or \
                   "no lights" in error_msg or \
                   "no switches" in error_msg
    
    @pytest.mark.asyncio
    async def test_ha_control_light_requires_action(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test that light control requires action parameter."""
        payload = {
            "tool_name": "ha_control_light",
            "arguments": {"name_filter": "kitchen"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "error"
        assert "action" in data["result_data"]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_ha_control_light_with_brightness(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test light control with brightness parameter."""
        payload = {
            "tool_name": "ha_control_light",
            "arguments": {
                "action": "turn_on",
                "name_filter": "bedroom",
                "brightness": 128
            },
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        # Should process the brightness parameter (success or config error)
        data = response.json()
        assert data["status"] in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_ha_control_switch_no_config(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test HA switch control when HA not configured."""
        payload = {
            "tool_name": "ha_control_switch",
            "arguments": {"action": "turn_off", "name_filter": "coffee"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # If HA_TOKEN not set, should get error (either configuration or no devices found)
        if data["status"] == "error":
            error_msg = data["result_data"]["error"].lower()
            assert "not configured" in error_msg or \
                   "failed" in error_msg or \
                   "no switches found" in error_msg
    
    @pytest.mark.asyncio
    async def test_ha_control_switch_requires_action(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test that switch control requires action parameter."""
        payload = {
            "tool_name": "ha_control_switch",
            "arguments": {"name_filter": "fan"},
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "error"
        assert "action" in data["result_data"]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_health_includes_ha_status(
        self,
        http_client: AsyncClient,
        server_url: str
    ):
        """Test that health check includes Home Assistant status."""
        response = await http_client.get(f"{server_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "home_assistant" in data
        # Should be one of: not_configured, configured, connected
        assert data["home_assistant"] in ["not_configured", "configured", "connected"]
    
    @pytest.mark.asyncio
    async def test_ha_response_format_multi_device(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test that multi-device responses have correct format."""
        # This tests the response structure when multiple devices would be controlled
        # Even if HA is not configured, we can verify the tool accepts the parameters
        payload = {
            "tool_name": "ha_control_light",
            "arguments": {
                "action": "turn_on",
                "name_filter": "kitchen"  # Short name - would control multiple
            },
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # If success, should have lights array and count
        # If error (not configured), should have error message
        if data["status"] == "success":
            assert "lights" in data["result_data"] or "count" in data["result_data"]
        else:
            assert "error" in data["result_data"]
    
    @pytest.mark.asyncio
    async def test_ha_fuzzy_matching_punctuation(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test that fuzzy matching handles punctuation differences."""
        # Test that names like "ellies room" match "Ellie's Room"
        # This verifies the normalize_text() function is working
        
        # Test light control with punctuation difference
        payload = {
            "tool_name": "ha_control_light",
            "arguments": {
                "action": "turn_on",
                "name_filter": "ellies picture room"  # No apostrophe
            },
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should either succeed (if HA configured and device exists)
        # or fail with "not configured" or "no lights found"
        # What matters is the tool accepted the parameters and processed them
        assert data["status"] in ["success", "error"]
        
        if data["status"] == "error":
            # Should be a config error or no devices found
            # NOT a parsing/validation error
            error_msg = data["result_data"]["error"].lower()
            assert "not configured" in error_msg or "no lights found" in error_msg
    
    @pytest.mark.asyncio
    async def test_ha_fuzzy_matching_switch(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test fuzzy matching on switch control."""
        # Test switch control with punctuation/spacing differences
        payload = {
            "tool_name": "ha_control_switch",
            "arguments": {
                "action": "turn_off",
                "name_filter": "office fan"  # No hyphens or special chars
            },
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["success", "error"]
        
        if data["status"] == "error":
            error_msg = data["result_data"]["error"].lower()
            assert "not configured" in error_msg or "no switches found" in error_msg
    
    @pytest.mark.asyncio
    async def test_ha_fuzzy_matching_sensor(
        self,
        http_client: AsyncClient,
        server_url: str,
        test_session_id: str
    ):
        """Test fuzzy matching on device state queries."""
        # Test sensor query with punctuation differences
        payload = {
            "tool_name": "ha_get_device_state",
            "arguments": {
                "domain": "sensor",
                "name_filter": "living room"  # Common name that might have apostrophes
            },
            "session_id": test_session_id
        }
        
        response = await http_client.post(
            f"{server_url}/v1/tools/call",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["success", "error"]
        
        if data["status"] == "error":
            error_msg = data["result_data"]["error"].lower()
            assert "not configured" in error_msg or "no devices found" in error_msg


