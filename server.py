import os
import json
import asyncio
import subprocess
import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from pydantic import BaseModel, Field
import redis.asyncio as redis
from redis.asyncio import Redis
from dotenv import load_dotenv
import httpx
import websockets

# Load environment variables from .env file
load_dotenv()

# External library for NTP
try:
    import ntplib
    NTP_CLIENT_AVAILABLE = True
except ImportError:
    ntplib = None
    NTP_CLIENT_AVAILABLE = False
    print("Warning: ntplib not installed. get_network_time will use system time as fallback.")

# --- Configuration & Initialization ---

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

NTP_SERVER = os.getenv("NTP_SERVER", "pool.ntp.org")
NTP_BACKUP_SERVER = os.getenv("NTP_BACKUP_SERVER", "time.google.com")
NTP_TIMEOUT = int(os.getenv("NTP_TIMEOUT", "5"))

SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Home Assistant Configuration
HA_URL = os.getenv("HA_URL", "http://ha.internal")
HA_TOKEN = os.getenv("HA_TOKEN", "")

# Timezone Configuration
LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE", "America/Los_Angeles")
HA_CACHE_TTL = int(os.getenv("HA_CACHE_TTL", "30"))

# Sunrise/Sunset API Configuration (configured in client .env)
SUN_API_URL = "https://api.sunrise-sunset.org/json"

redis_client: Optional[Redis] = None
ha_service: Optional['HomeAssistantService'] = None
app_id = "mcp-server-project" 

# --- Pydantic Schemas ---

class ToolDefinition(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A clear description of the tool's purpose.")
    parameters: Dict[str, Any] = Field(..., description="JSON schema defining the input parameters for the tool.")

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="The name of the tool to be executed.")
    arguments: Dict[str, Any] = Field(..., description="The arguments needed for the tool execution.")
    session_id: str = Field(..., description="Unique ID for the user/session context.")

class ToolCallResponse(BaseModel):
    status: str = Field(..., description="Execution status: 'success' or 'error'.")
    result_data: Dict[str, Any] = Field(..., description="The data or output returned by the tool.")

class LLMGenerateRequest(BaseModel):
    session_id: str = Field(..., description="The context session ID.")
    prompt: str = Field(..., description="The user's query.")

class LLMGenerateResponse(BaseModel):
    response_text: str = Field(..., description="The model's final response.")
    is_cached: bool = Field(False, description="Whether the response came from the cache.")

# --- Services (Core Logic) ---

def get_redis_client() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client not initialized.")
    return redis_client


class HomeAssistantService:
    """Manages Home Assistant WebSocket connection and device state caching."""
    
    def __init__(self, url: str, token: str, cache_ttl: int = 30):
        self.url = url.rstrip('/')
        self.token = token
        self.cache_ttl = cache_ttl
        self.ws = None
        self.ws_task = None
        self.message_id = 1
        self._connected = False
        
    async def connect(self):
        """Establish WebSocket connection to Home Assistant."""
        if not self.token:
            print("Warning: HA_TOKEN not set. Home Assistant integration disabled.")
            return
            
        ws_url = self.url.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/websocket'
        
        try:
            self.ws_task = asyncio.create_task(self._maintain_connection(ws_url))
            print(f"Home Assistant WebSocket connection initiated to {ws_url}")
        except Exception as e:
            print(f"Failed to start Home Assistant WebSocket: {e}")
    
    async def _maintain_connection(self, ws_url: str):
        """Maintain WebSocket connection with reconnection logic."""
        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.ws = websocket
                    
                    # Receive auth required message
                    auth_msg = json.loads(await websocket.recv())
                    if auth_msg.get('type') == 'auth_required':
                        # Send auth
                        await websocket.send(json.dumps({
                            'type': 'auth',
                            'access_token': self.token
                        }))
                        
                        # Wait for auth result
                        auth_result = json.loads(await websocket.recv())
                        if auth_result.get('type') == 'auth_ok':
                            print("Home Assistant WebSocket authenticated successfully")
                            self._connected = True
                            
                            # Subscribe to state changes
                            await self._subscribe_to_events(websocket)
                            
                            # Listen for state changes
                            async for message in websocket:
                                await self._handle_message(json.loads(message))
                        else:
                            print(f"Home Assistant auth failed: {auth_result}")
                            break
                            
            except Exception as e:
                print(f"Home Assistant WebSocket error: {e}. Reconnecting in 5s...")
                self._connected = False
                await asyncio.sleep(5)
    
    async def _subscribe_to_events(self, websocket):
        """Subscribe to state_changed events."""
        await websocket.send(json.dumps({
            'id': self.message_id,
            'type': 'subscribe_events',
            'event_type': 'state_changed'
        }))
        self.message_id += 1
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket messages and update Redis cache."""
        if message.get('type') == 'event' and message.get('event', {}).get('event_type') == 'state_changed':
            data = message['event']['data']
            entity_id = data.get('entity_id')
            new_state = data.get('new_state')
            
            if entity_id and new_state and redis_client:
                # Cache the state in Redis
                cache_key = f"ha:state:{entity_id}"
                try:
                    await redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(new_state)
                    )
                except Exception as e:
                    print(f"Failed to cache HA state for {entity_id}: {e}")
    
    async def get_states(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all states from Home Assistant, optionally filtered by domain."""
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
                response = await client.get(f"{self.url}/api/states", headers=headers, timeout=10.0)
                response.raise_for_status()
                
                states = response.json()
                
                # Filter by domain if specified
                if domain:
                    states = [s for s in states if s['entity_id'].startswith(f"{domain}.")]
                
                return states
            except Exception as e:
                raise RuntimeError(f"Failed to fetch Home Assistant states: {e}")
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific entity, checking cache first."""
        # Try cache first
        if redis_client:
            cache_key = f"ha:state:{entity_id}"
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Cache read error for {entity_id}: {e}")
        
        # Fetch from API
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
                response = await client.get(f"{self.url}/api/states/{entity_id}", headers=headers, timeout=10.0)
                response.raise_for_status()
                state = response.json()
                
                # Cache it
                if redis_client:
                    try:
                        await redis_client.setex(
                            f"ha:state:{entity_id}",
                            self.cache_ttl,
                            json.dumps(state)
                        )
                    except Exception:
                        pass
                
                return state
            except Exception as e:
                raise RuntimeError(f"Failed to fetch state for {entity_id}: {e}")
    
    async def call_service(self, domain: str, service: str, entity_id: str, **kwargs) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
                
                service_data = {'entity_id': entity_id}
                service_data.update(kwargs)
                
                response = await client.post(
                    f"{self.url}/api/services/{domain}/{service}",
                    headers=headers,
                    json=service_data,
                    timeout=10.0
                )
                response.raise_for_status()
                
                # Invalidate cache for this entity after state change
                if redis_client:
                    try:
                        await redis_client.delete(f"ha:state:{entity_id}")
                    except Exception:
                        pass
                
                return {'success': True, 'entity_id': entity_id, 'service': f"{domain}.{service}"}
            except Exception as e:
                raise RuntimeError(f"Failed to call service {domain}.{service}: {e}")
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self._connected = False
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()


class ToolService:
    """Manages the available tools and their execution logic."""

    NTP_SERVERS = [NTP_SERVER, NTP_BACKUP_SERVER]
    PING_COUNT = 4

    TOOLS: Dict[str, ToolDefinition] = {
        "get_network_time": ToolDefinition( 
            name="get_network_time",
            description="Retrieves the current accurate time and date from a network source (NTP). Useful for answering 'What time is it?' or 'What is the date?'.",
            parameters={"type": "object", "properties": {}},
        ),
        "ping_host": ToolDefinition( 
            name="ping_host",
            description="Sends a network ping request to a specified hostname or IP address to check connectivity and latency.",
            parameters={
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "The hostname or IP address to ping (e.g., 'google.com')."},
                },
                "required": ["hostname"]
            },
        ),
        "ha_get_device_state": ToolDefinition(
            name="ha_get_device_state",
            description="Get the current state of a Home Assistant device or sensor. Use for temperature sensors, humidity, battery levels, or checking device status. Supports filtering by domain (sensor, binary_sensor, etc.).",
            parameters={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID to query (e.g., 'sensor.living_room_temperature'). Optional if using domain filter."
                    },
                    "domain": {
                        "type": "string", 
                        "description": "Filter devices by domain: 'sensor' for sensors, 'binary_sensor' for on/off sensors, 'climate' for thermostats, etc. Returns all matching devices."
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Optional filter to match device names (case-insensitive, partial match)."
                    }
                },
                "required": []
            },
        ),
        "ha_control_light": ToolDefinition(
            name="ha_control_light",
            description="Control Home Assistant lights. Turn on/off, set brightness (0-255), or change color. Use this when user mentions lights, lamps, or illumination.",
            parameters={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The light entity ID (e.g., 'light.living_room'). Use name_filter to find lights by name."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "toggle"],
                        "description": "The action to perform on the light."
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "Brightness level 0-255 (only when turning on).",
                        "minimum": 0,
                        "maximum": 255
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Find light by name (e.g., 'living room', 'bedroom'). Returns first match."
                    }
                },
                "required": ["action"]
            },
        ),
        "ha_control_switch": ToolDefinition(
            name="ha_control_switch",
            description="Control Home Assistant switches. Turn on/off or toggle switches. Use for outlets, relays, or any switchable devices.",
            parameters={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The switch entity ID (e.g., 'switch.coffee_maker'). Use name_filter to find by name."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "toggle"],
                        "description": "The action to perform on the switch."
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Find switch by name (e.g., 'coffee maker', 'fan'). Returns first match."
                    }
                },
                "required": ["action"]
            },
        ),
        "get_sun_times": ToolDefinition(
            name="get_sun_times",
            description="Get sunrise and sunset times for a specific location and date. Returns sunrise, sunset, solar noon, day length, and twilight times. Use for queries like 'when is sunrise?', 'what time is sunset?', 'when does the sun set today?'.",
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (e.g., '2024-12-25'). Defaults to today if not specified."
                    },
                    "formatted": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "0 for ISO 8601 format (24-hour), 1 for 12-hour AM/PM format. Defaults to 0."
                    }
                },
                "required": []
            },
        ),
    }

    def list_tools(self) -> List[ToolDefinition]:
        return list(self.TOOLS.values())

    async def _execute_ntp_sync(self) -> ToolCallResponse:
        """Helper to execute the blocking NTP sync logic in a separate thread."""
        try:
            local_tz = ZoneInfo(LOCAL_TIMEZONE)
        except Exception:
            local_tz = ZoneInfo("America/Los_Angeles")  # Fallback
            
        if not NTP_CLIENT_AVAILABLE:
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(local_tz)
            return ToolCallResponse(status="success", result_data={
                "timestamp_utc": now_utc.isoformat(),
                "timestamp_local": now_local.isoformat(),
                "readable_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "readable_time_local": now_local.strftime("%Y-%m-%d %I:%M:%S %p %Z"),
                "timezone": LOCAL_TIMEZONE,
                "source": "System Time (NTP client unavailable)"
            })
            
        c = ntplib.NTPClient()
        server_to_use = self.NTP_SERVERS[0]
        try:
            response = await asyncio.to_thread(c.request, server_to_use, version=3, timeout=NTP_TIMEOUT)
            ntp_time_utc = datetime.fromtimestamp(response.tx_time, timezone.utc)
            ntp_time_local = ntp_time_utc.astimezone(local_tz)
            return ToolCallResponse(status="success", result_data={
                "timestamp_utc": ntp_time_utc.isoformat(),
                "timestamp_local": ntp_time_local.isoformat(),
                "readable_time_utc": ntp_time_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "readable_time_local": ntp_time_local.strftime("%Y-%m-%d %I:%M:%S %p %Z"),
                "timezone": LOCAL_TIMEZONE,
                "offset_ms": round(response.offset * 1000, 2),
                "source": f"NTP Server: {server_to_use}"
            })
        except ntplib.NTPException as e:
            return ToolCallResponse(status="error", result_data={"error": f"NTP synchronization failed: {e}"})
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": f"An unexpected error occurred during NTP sync: {e}"})
            
    async def _execute_ping(self, hostname: str) -> ToolCallResponse:
        """Helper to execute the blocking subprocess ping command in a separate thread and parse output."""
        
        if os.name == 'nt':
            command = f"ping -n {self.PING_COUNT} {hostname}"
        else:
            command = f"ping -c {self.PING_COUNT} {hostname}"

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                shell=True
            )
            
            output = result.stdout.strip() + "\n" + result.stderr.strip()
            
            # --- COPILOT TASK 1: ROBUST PING PARSING ---
            
            # 1. Packet Loss Parsing
            loss_match = re.search(r"(\d+)% packet loss", output)
            packet_loss_percent = int(loss_match.group(1)) if loss_match else 100 if result.returncode != 0 else 0
            is_success = packet_loss_percent < 100
            
            # 2. Latency Parsing (Standardizing across Windows/Linux/Mac)
            latency_match = re.search(r"Average = ([\d\.]+)ms|min/avg/max/mdev = [\d\.]+/([\d\.]+)/", output, re.IGNORECASE)
            average_latency = "N/A"
            if latency_match:
                average_latency = latency_match.group(1) if latency_match.group(1) else latency_match.group(2)
            
            status_message = "Host Reachable" if is_success else "Host Unreachable"
            
            # END COPILOT TASK 1
            
            return ToolCallResponse(status="success" if is_success else "error", result_data={
                "host": hostname,
                "status": status_message,
                "average_latency_ms": average_latency,
                "packet_loss_percent": packet_loss_percent,
                "full_output_snippet": output[:500] # Snippet for context
            })

        except subprocess.TimeoutExpired:
            return ToolCallResponse(status="error", result_data={"error": f"Ping command timed out after 5 seconds for host: {hostname}"})
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": f"Failed to execute ping command: {e}"})

    async def _execute_ha_get_device_state(self, domain: Optional[str] = None, entity_id: Optional[str] = None, name_filter: Optional[str] = None) -> ToolCallResponse:
        """Get state of Home Assistant devices/sensors."""
        if not ha_service or not ha_service.token:
            return ToolCallResponse(status="error", result_data={"error": "Home Assistant not configured. Set HA_URL and HA_TOKEN in .env"})
        
        def normalize_text(text: str) -> str:
            """Remove punctuation and normalize spaces for fuzzy matching."""
            # Convert underscores to spaces first, then remove all punctuation
            text = text.replace('_', ' ')
            text = re.sub(r'[^\w\s]', '', text.lower())
            # Normalize whitespace (collapse multiple spaces to single space)
            text = re.sub(r'\s+', ' ', text).strip()
            # Remove plural 's' at the end for better matching (lamps → lamp)
            if text.endswith('s') and len(text) > 3:
                text = text[:-1]
            return text
        
        try:
            # If entity_id provided, get specific entity
            if entity_id:
                state = await ha_service.get_state(entity_id)
                return ToolCallResponse(status="success", result_data={
                    "entity_id": state['entity_id'],
                    "state": state['state'],
                    "attributes": state.get('attributes', {}),
                    "last_changed": state.get('last_changed'),
                    "last_updated": state.get('last_updated')
                })
            
            # Otherwise, get states filtered by domain/name
            states = await ha_service.get_states(domain=domain)
            
            # Apply name filter if provided with improved fuzzy matching
            if name_filter:
                normalized_filter = normalize_text(name_filter)
                # Extract main keywords from filter
                filter_keywords = [w for w in normalized_filter.split() if w not in ['and', 'or', 'the'] and not w.isdigit()]
                
                filtered_states = []
                for s in states:
                    device_name = normalize_text(s.get('attributes', {}).get('friendly_name', ''))
                    entity_id = normalize_text(s['entity_id'])
                    
                    # Check if filter matches device name sufficiently
                    if normalized_filter in device_name or device_name in normalized_filter or normalized_filter in entity_id:
                        filtered_states.append(s)
                    elif len(filter_keywords) >= 2:
                        matched_keywords = sum(1 for keyword in filter_keywords if keyword in device_name)
                        if matched_keywords >= len(filter_keywords):
                            filtered_states.append(s)
                
                states = filtered_states
            
            if not states:
                filter_desc = f"domain={domain}" if domain else "all"
                if name_filter:
                    filter_desc += f", name={name_filter}"
                return ToolCallResponse(status="error", result_data={"error": f"No devices found with filter: {filter_desc}"})
            
            # Return summary of devices
            devices = []
            for s in states[:20]:  # Limit to 20 devices
                devices.append({
                    "entity_id": s['entity_id'],
                    "name": s.get('attributes', {}).get('friendly_name', s['entity_id']),
                    "state": s['state'],
                    "unit": s.get('attributes', {}).get('unit_of_measurement'),
                    "device_class": s.get('attributes', {}).get('device_class')
                })
            
            return ToolCallResponse(status="success", result_data={
                "count": len(devices),
                "devices": devices,
                "note": f"Showing {len(devices)} of {len(states)} matching devices" if len(states) > 20 else None
            })
            
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": f"Failed to get HA state: {e}"})

    async def _execute_ha_control_light(self, action: str, entity_id: Optional[str] = None, name_filter: Optional[str] = None, brightness: Optional[int] = None) -> ToolCallResponse:
        """Control Home Assistant lights."""
        if not ha_service or not ha_service.token:
            return ToolCallResponse(status="error", result_data={"error": "Home Assistant not configured. Set HA_URL and HA_TOKEN in .env"})
        
        def normalize_text(text: str) -> str:
            """Remove punctuation and normalize spaces for fuzzy matching."""
            # Convert underscores to spaces first, then remove all punctuation
            text = text.replace('_', ' ')
            text = re.sub(r'[^\w\s]', '', text.lower())
            # Normalize whitespace (collapse multiple spaces to single space)
            text = re.sub(r'\s+', ' ', text).strip()
            # Remove plural 's' at the end for better matching (lamps → lamp)
            if text.endswith('s') and len(text) > 3:
                text = text[:-1]
            return text
        
        try:
            entities_to_control = []
            
            # If entity_id provided directly, use it
            if entity_id:
                entities_to_control = [entity_id]
            elif name_filter:
                # Find matching lights with improved fuzzy matching
                lights = await ha_service.get_states(domain='light')
                normalized_filter = normalize_text(name_filter)
                
                # Extract main keywords from filter (ignore numbers, 'and', etc.)
                filter_keywords = [w for w in normalized_filter.split() if w not in ['and', 'or', 'the'] and not w.isdigit()]
                
                matching = []
                for l in lights:
                    device_name = normalize_text(l.get('attributes', {}).get('friendly_name', ''))
                    entity_id = normalize_text(l['entity_id'])
                    
                    # Check if filter matches device name sufficiently
                    # Direct substring match (either direction)
                    if normalized_filter in device_name or device_name in normalized_filter or normalized_filter in entity_id:
                        matching.append(l)
                    # Or if multiple keywords match (not just one)
                    elif len(filter_keywords) >= 2:
                        matched_keywords = sum(1 for keyword in filter_keywords if keyword in device_name)
                        if matched_keywords >= len(filter_keywords):  # All keywords must match
                            matching.append(l)
                
                # If no lights found, check switches (many lamps are plugged into smart switches)
                if not matching:
                    switches = await ha_service.get_states(domain='switch')
                    
                    for s in switches:
                        device_name = normalize_text(s.get('attributes', {}).get('friendly_name', ''))
                        entity_id = normalize_text(s['entity_id'])
                        
                        # Check if filter matches device name sufficiently
                        if normalized_filter in device_name or device_name in normalized_filter or normalized_filter in entity_id:
                            matching.append(s)
                        elif len(filter_keywords) >= 2:
                            matched_keywords = sum(1 for keyword in filter_keywords if keyword in device_name)
                            if matched_keywords >= len(filter_keywords):
                                matching.append(s)
                    
                    if matching:
                        # Found switches matching - use switch control instead
                        return await self._execute_ha_control_switch(action, name_filter=name_filter)
                
                if not matching:
                    return ToolCallResponse(status="error", result_data={"error": f"No lights or switches found matching '{name_filter}'"})
                
                # Determine if user wants specific light or all in area
                # If name_filter is long (>2 words) or very specific, control only best match
                # Otherwise control all matching lights
                word_count = len(name_filter.split())
                
                if word_count >= 3:
                    # Specific light name (e.g., "kitchen above cabinet light")
                    # Find the best match (most words in common)
                    best_match = max(matching, key=lambda l: len([
                        w for w in normalized_filter.split() 
                        if w in normalize_text(l.get('attributes', {}).get('friendly_name', ''))
                    ]))
                    entities_to_control = [best_match['entity_id']]
                else:
                    # General room/area name (e.g., "kitchen" or "kitchen lights")
                    # Control all matching lights
                    entities_to_control = [l['entity_id'] for l in matching]
            else:
                return ToolCallResponse(status="error", result_data={"error": "Either entity_id or name_filter must be provided"})
            
            # Call service for each matching entity
            service_kwargs = {}
            if action == "turn_on" and brightness is not None:
                service_kwargs['brightness'] = brightness
            
            results = []
            for entity in entities_to_control:
                try:
                    result = await ha_service.call_service('light', action, entity, **service_kwargs)
                    
                    # Give HA a longer moment to update state (sometimes takes a bit)
                    await asyncio.sleep(0.5)
                    
                    # Force cache invalidation before fetching new state
                    if redis_client:
                        try:
                            await redis_client.delete(f"ha:state:{entity}")
                        except Exception:
                            pass
                    
                    # Fetch fresh state (cache was invalidated in call_service)
                    new_state = await ha_service.get_state(entity)
                    results.append({
                        "entity_id": entity,
                        "friendly_name": new_state.get('attributes', {}).get('friendly_name', entity),
                        "new_state": new_state['state'],
                        "brightness": new_state.get('attributes', {}).get('brightness')
                    })
                except Exception as e:
                    results.append({
                        "entity_id": entity,
                        "error": str(e)
                    })
            
            return ToolCallResponse(status="success", result_data={
                "action": action,
                "count": len(results),
                "lights": results
            })
            
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": f"Failed to control lights: {e}"})

    async def _execute_ha_control_switch(self, action: str, entity_id: Optional[str] = None, name_filter: Optional[str] = None) -> ToolCallResponse:
        """Control Home Assistant switches."""
        if not ha_service or not ha_service.token:
            return ToolCallResponse(status="error", result_data={"error": "Home Assistant not configured. Set HA_URL and HA_TOKEN in .env"})
        
        def normalize_text(text: str) -> str:
            """Remove punctuation and normalize spaces for fuzzy matching."""
            # Convert underscores to spaces first, then remove all punctuation
            text = text.replace('_', ' ')
            text = re.sub(r'[^\w\s]', '', text.lower())
            # Normalize whitespace (collapse multiple spaces to single space)
            text = re.sub(r'\s+', ' ', text).strip()
            # Remove plural 's' at the end for better matching (lamps → lamp)
            if text.endswith('s') and len(text) > 3:
                text = text[:-1]
            return text
        
        try:
            entities_to_control = []
            
            # If entity_id provided directly, use it
            if entity_id:
                entities_to_control = [entity_id]
            elif name_filter:
                # Find matching switches with improved fuzzy matching
                switches = await ha_service.get_states(domain='switch')
                normalized_filter = normalize_text(name_filter)
                
                # Extract main keywords from filter (ignore numbers, 'and', etc.)
                filter_keywords = [w for w in normalized_filter.split() if w not in ['and', 'or', 'the'] and not w.isdigit()]
                
                matching = []
                for s in switches:
                    device_name = normalize_text(s.get('attributes', {}).get('friendly_name', ''))
                    entity_id = normalize_text(s['entity_id'])
                    
                    # Check if filter matches device name sufficiently
                    if normalized_filter in device_name or device_name in normalized_filter or normalized_filter in entity_id:
                        matching.append(s)
                    elif len(filter_keywords) >= 2:
                        matched_keywords = sum(1 for keyword in filter_keywords if keyword in device_name)
                        if matched_keywords >= len(filter_keywords):
                            matching.append(s)
                
                if not matching:
                    return ToolCallResponse(status="error", result_data={"error": f"No switches found matching '{name_filter}'"})
                
                # Determine if user wants specific switch or all in area
                # If name_filter is long (>2 words) or very specific, control only best match
                # Otherwise control all matching switches
                word_count = len(name_filter.split())
                
                if word_count >= 3:
                    # Specific switch name (e.g., "kitchen coffee maker switch")
                    # Find the best match (most words in common)
                    best_match = max(matching, key=lambda s: len([
                        w for w in normalized_filter.split() 
                        if w in normalize_text(s.get('attributes', {}).get('friendly_name', ''))
                    ]))
                    entities_to_control = [best_match['entity_id']]
                else:
                    # General area name (e.g., "kitchen" or "kitchen switches")
                    # Control all matching switches
                    entities_to_control = [s['entity_id'] for s in matching]
            else:
                return ToolCallResponse(status="error", result_data={"error": "Either entity_id or name_filter must be provided"})
            
            # Call service for each matching entity
            results = []
            for entity in entities_to_control:
                try:
                    result = await ha_service.call_service('switch', action, entity)
                    
                    # Give HA a longer moment to update state (sometimes takes a bit)
                    await asyncio.sleep(0.5)
                    
                    # Force cache invalidation before fetching new state
                    if redis_client:
                        try:
                            await redis_client.delete(f"ha:state:{entity}")
                        except Exception:
                            pass
                    
                    # Fetch fresh state (cache was invalidated in call_service)
                    new_state = await ha_service.get_state(entity)
                    results.append({
                        "entity_id": entity,
                        "friendly_name": new_state.get('attributes', {}).get('friendly_name', entity),
                        "new_state": new_state['state']
                    })
                except Exception as e:
                    results.append({
                        "entity_id": entity,
                        "error": str(e)
                    })
            
            return ToolCallResponse(status="success", result_data={
                "action": action,
                "count": len(results),
                "switches": results
            })
            
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": f"Failed to control switches: {e}"})

    async def _execute_get_sun_times(self, date: Optional[str] = None, formatted: int = 0, lat: Optional[float] = None, lng: Optional[float] = None) -> ToolCallResponse:
        """Get sunrise and sunset times from sunrise-sunset.org API."""
        if lat is None or lng is None:
            return ToolCallResponse(status="error", result_data={
                "error": "Latitude and longitude not configured. Please set SUN_LAT and SUN_LNG in .env.client"
            })
        
        try:
            # Build request URL
            params = {
                "lat": lat,
                "lng": lng,
                "formatted": formatted
            }
            
            # Add date if provided
            if date:
                params["date"] = date
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.get(SUN_API_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    return ToolCallResponse(status="error", result_data={
                        "error": f"Sunrise-Sunset API error: {data.get('status', 'UNKNOWN')}"
                    })
                
                results = data.get("results", {})
                
                return ToolCallResponse(status="success", result_data={
                    "sunrise": results.get("sunrise"),
                    "sunset": results.get("sunset"),
                    "solar_noon": results.get("solar_noon"),
                    "day_length": results.get("day_length"),
                    "civil_twilight_begin": results.get("civil_twilight_begin"),
                    "civil_twilight_end": results.get("civil_twilight_end"),
                    "nautical_twilight_begin": results.get("nautical_twilight_begin"),
                    "nautical_twilight_end": results.get("nautical_twilight_end"),
                    "astronomical_twilight_begin": results.get("astronomical_twilight_begin"),
                    "astronomical_twilight_end": results.get("astronomical_twilight_end"),
                    "location": {"latitude": lat, "longitude": lng},
                    "date": date if date else "today",
                    "timezone": "UTC" if formatted == 0 else "Local"
                })
                
        except httpx.HTTPError as e:
            return ToolCallResponse(status="error", result_data={
                "error": f"Failed to fetch sun times: {e}"
            })
        except Exception as e:
            return ToolCallResponse(status="error", result_data={
                "error": f"Unexpected error getting sun times: {e}"
            })


    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCallResponse:
        if tool_name not in self.TOOLS:
            return ToolCallResponse(status="error", result_data={"error": f"Unknown tool: {tool_name}"})

        try:
            if tool_name == "get_network_time":
                return await self._execute_ntp_sync()
            elif tool_name == "ping_host":
                hostname = arguments.get("hostname")
                if not hostname: raise ValueError("Hostname is required.")
                return await self._execute_ping(hostname)
            elif tool_name == "ha_get_device_state":
                return await self._execute_ha_get_device_state(
                    entity_id=arguments.get("entity_id"),
                    domain=arguments.get("domain"),
                    name_filter=arguments.get("name_filter")
                )
            elif tool_name == "ha_control_light":
                action = arguments.get("action")
                if not action:
                    raise ValueError("Action is required (turn_on, turn_off, or toggle)")
                return await self._execute_ha_control_light(
                    action=action,
                    entity_id=arguments.get("entity_id"),
                    name_filter=arguments.get("name_filter"),
                    brightness=arguments.get("brightness")
                )
            elif tool_name == "ha_control_switch":
                action = arguments.get("action")
                if not action:
                    raise ValueError("Action is required (turn_on, turn_off, or toggle)")
                return await self._execute_ha_control_switch(
                    action=action,
                    entity_id=arguments.get("entity_id"),
                    name_filter=arguments.get("name_filter")
                )
            elif tool_name == "get_sun_times":
                # Get lat/lng from arguments (passed by client)
                lat = arguments.get("lat")
                lng = arguments.get("lng")
                return await self._execute_get_sun_times(
                    date=arguments.get("date"),
                    formatted=arguments.get("formatted", 0),
                    lat=lat,
                    lng=lng
                )
            else:
                 return ToolCallResponse(status="error", result_data={"error": "Tool logic not yet implemented."})
        except Exception as e:
            return ToolCallResponse(status="error", result_data={"error": str(e)})


class LLMService:
    """Handles interaction with the language model backend (API or local)."""

    def __init__(self, tool_service: ToolService):
        self.tool_service = tool_service

    async def generate(self, session_id: str, prompt: str) -> LLMGenerateResponse:
        """
        Main function to handle LLM generation, caching, and tool reasoning loop.
        """
        r = get_redis_client()
        # COPILOT TASK 2: Implement robust caching key generation and retrieval
        cache_key = f"cache:prompt:{session_id}:{hash(prompt)}" 
        
        cached_response = await r.get(cache_key)
        if cached_response:
            return LLMGenerateResponse(
                response_text=cached_response.decode("utf-8"), 
                is_cached=True
            )

        tools_list = self.tool_service.list_tools()
        tools_json = json.dumps([t.model_dump() for t in tools_list])

        # --- COPILOT TASK 3: IMPLEMENT LLM INTEGRATION AND TOOL-USE LOOP ---
        
        # Placeholder for LLM Integration (Replace this with actual LLM API/Client calls)
        # Assume LLM is Anthropic Claude, OpenAI GPT, or a local ollama endpoint.
        
        # 1. First LLM Call (Passing the prompt and the available tools_json)
        # response_1 = llm_client.generate(prompt=prompt, tools=tools_json)
        
        # Mock LLM Logic: If prompt contains 'time', LLM responds with a tool call request.
        if "time" in prompt.lower() and "time:" not in prompt.lower():
             # Simulate LLM deciding to call a tool
             mock_tool_call_request = ToolCallRequest(tool_name="get_network_time", arguments={}, session_id=session_id)
             print(f"LLM suggested tool call: {mock_tool_call_request.tool_name}")
             
             # 2. Execute Tool Call (Calling the server's own logic)
             tool_response = await self.tool_service.call_tool(mock_tool_call_request.tool_name, mock_tool_call_request.arguments)
             tool_result_str = json.dumps(tool_response.result_data)
             
             # 3. Second LLM Call (Passing the original prompt + Tool Result for final generation)
             final_prompt = f"{prompt}\n\nTool Result for {mock_tool_call_request.tool_name}:\n{tool_result_str}"
             # final_response_text = llm_client.generate(prompt=final_prompt)
             
             # Mock Final Response
             mock_final_response = f"Based on the network time tool, the current time is: {tool_response.result_data.get('readable_time', 'unknown')}"
             
        else:
             mock_final_response = f"Hello! The MCP server is running. I see you asked about: '{prompt}'. I have {len(tools_list)} tools available for use."
        
        # END COPILOT TASK 3
        
        # 4. Cache the successful result
        await r.set(cache_key, mock_final_response, ex=3600)

        return LLMGenerateResponse(
            response_text=mock_final_response,
            is_cached=False
        )

# --- FastAPI Application ---

app = FastAPI(
    title="Model Context Protocol (MCP) Server Scaffold",
    version="1.0.0",
    description="A Python FastAPI server to implement a Model Context Protocol (MCP) server with Redis caching.",
)

@app.on_event("startup")
async def startup_event():
    """Connect to Redis and Home Assistant on application startup."""
    global redis_client, ha_service
    # COPILOT TASK 4: Implement robust Redis connection logic (connection pooling, resilience)
    try:
        redis_config = {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "db": REDIS_DB,
            "decode_responses": True
        }
        if REDIS_PASSWORD:
            redis_config["password"] = REDIS_PASSWORD
            
        redis_client = redis.Redis(**redis_config)
        await redis_client.ping()
        print(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})")
    except Exception as e:
        print(f"Could not connect to Redis: {e}")
        redis_client = None
    
    # Initialize Home Assistant service
    ha_service = HomeAssistantService(HA_URL, HA_TOKEN, HA_CACHE_TTL)
    await ha_service.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis and Home Assistant connections on application shutdown."""
    if redis_client:
        await redis_client.close()
    if ha_service:
        await ha_service.disconnect()

# Initialize services
tool_service = ToolService()
llm_service = LLMService(tool_service=tool_service)

# --- Endpoints ---

@app.get("/health")
async def health_check():
    redis_status = "connected" if redis_client and await redis_client.ping() else "disconnected"
    ha_status = "connected" if ha_service and ha_service._connected else ("configured" if ha_service and ha_service.token else "not_configured")
    return {
        "status": "ok", 
        "service": "mcp-server", 
        "redis": redis_status,
        "home_assistant": ha_status
    }

@app.get("/v1/tools/list", response_model=List[ToolDefinition])
async def list_tools_endpoint():
    return tool_service.list_tools()

@app.post("/v1/tools/call", response_model=ToolCallResponse)
async def call_tool_endpoint(request: ToolCallRequest):
    print(f"Client requested tool call: {request.tool_name} with args: {request.arguments}")
    return await tool_service.call_tool(request.tool_name, request.arguments)

@app.post("/v1/generate", response_model=LLMGenerateResponse)
async def generate_response(request: LLMGenerateRequest):
    return await llm_service.generate(request.session_id, request.prompt)