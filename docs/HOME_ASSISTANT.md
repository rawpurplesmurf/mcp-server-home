# Home Assistant Integration

Complete guide to Home Assistant integration with the MCP Server.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Available Tools](#available-tools)
- [Smart Multi-Device Control](#smart-multi-device-control)
- [WebSocket Integration](#websocket-integration)
- [Redis Caching](#redis-caching)
- [Client Shortcuts](#client-shortcuts)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The MCP Server provides deep integration with Home Assistant, allowing you to:
- Query device states (sensors, lights, switches, climate, etc.)
- Control lights with brightness control
- Control switches
- Smart multi-device control (automatic detection of broad vs. specific queries)
- Real-time state updates via WebSocket
- Intelligent caching with Redis

## Setup

### Prerequisites
- Home Assistant instance (local or remote)
- Long-lived access token
- (Optional) Redis for caching

### Step 1: Generate Access Token

1. Open your Home Assistant web interface
2. Click on your profile icon (bottom left)
3. Scroll down to "Security" section
4. Under "Long-Lived Access Tokens", click "Create Token"
5. Give it a descriptive name (e.g., "MCP Server")
6. Copy the token immediately (you won't see it again)

### Step 2: Configure Environment

Edit your `.env` file:

```bash
# Home Assistant Configuration
HA_URL=http://homeassistant.local:8123  # Your HA instance URL
HA_TOKEN=your_long_lived_access_token_here
HA_CACHE_TTL=30  # Cache device states for 30 seconds (optional)
```

### Step 3: Verify Connection

Restart the MCP Server and check the health endpoint:

```bash
curl http://localhost:8000/health
```

Look for:
```json
{
  "status": "healthy",
  "home_assistant": "connected",
  ...
}
```

## Available Tools

### 1. `ha_get_device_state`

Query the state of Home Assistant devices.

**Parameters:**
- `domain` (optional): Filter by device domain (sensor, light, switch, climate, etc.)
- `name_filter` (optional): Filter by device name (case-insensitive partial match)

**Returns:**
- List of matching devices with their states, attributes, and metadata

**Example:**
```json
{
  "tool_name": "ha_get_device_state",
  "arguments": {
    "domain": "sensor",
    "name_filter": "temperature"
  }
}
```

### 2. `ha_control_light`

Control Home Assistant lights.

**Parameters:**
- `action` (required): `turn_on`, `turn_off`, or `toggle`
- `name_filter` (optional): Device name to match
- `entity_id` (optional): Specific entity ID
- `brightness` (optional): Brightness level (0-255, only for `turn_on`)

**Returns:**
- `count`: Number of lights controlled
- `lights`: Array of light objects with new state

**Example:**
```json
{
  "tool_name": "ha_control_light",
  "arguments": {
    "action": "turn_on",
    "name_filter": "kitchen",
    "brightness": 200
  }
}
```

### 3. `ha_control_switch`

Control Home Assistant switches.

**Parameters:**
- `action` (required): `turn_on`, `turn_off`, or `toggle`
- `name_filter` (optional): Device name to match
- `entity_id` (optional): Specific entity ID

**Returns:**
- `count`: Number of switches controlled
- `switches`: Array of switch objects with new state

**Example:**
```json
{
  "tool_name": "ha_control_switch",
  "arguments": {
    "action": "toggle",
    "name_filter": "coffee maker"
  }
}
```

## Smart Multi-Device Control

The MCP Server intelligently determines whether to control one device or multiple based on query specificity.

### Broad Queries (1-2 words) → Controls ALL matching devices

When your query is short and general, all matching devices are controlled:

**Examples:**
- `"Turn on kitchen lights"` → All lights with "kitchen" in the name
- `"Turn off bedroom"` → All bedroom devices
- `"Toggle office lights"` → All office lights

**Response format:**
```json
{
  "action": "turn_on",
  "count": 3,
  "lights": [
    {
      "entity_id": "light.kitchen_ceiling",
      "friendly_name": "Kitchen Ceiling",
      "new_state": "on",
      "brightness": 255
    },
    {
      "entity_id": "light.kitchen_cabinet",
      "friendly_name": "Kitchen Above Cabinet",
      "new_state": "on",
      "brightness": 255
    },
    {
      "entity_id": "light.kitchen_island",
      "friendly_name": "Kitchen Island",
      "new_state": "on",
      "brightness": 255
    }
  ]
}
```

### Specific Queries (3+ words) → Controls ONE specific device

When your query is detailed and specific, only the best matching device is controlled:

**Examples:**
- `"Turn off the kitchen above cabinet light"` → Only that specific light
- `"Turn on the living room reading lamp"` → Only the reading lamp
- `"Toggle the bedroom ceiling fan switch"` → Only that switch

**Response format:**
```json
{
  "action": "turn_off",
  "count": 1,
  "lights": [
    {
      "entity_id": "light.kitchen_cabinet",
      "friendly_name": "Kitchen Above Cabinet",
      "new_state": "off",
      "brightness": null
    }
  ]
}
```

### Algorithm

The system uses word count to determine intent:

1. **Extract target name**: Remove action words ("turn on", "turn off", "toggle", "the")
2. **Count words**: Split remaining text by spaces
3. **Apply logic**:
   - `word_count < 3`: Control ALL matching devices
   - `word_count >= 3`: Find best match using fuzzy scoring, control only that one

## WebSocket Integration

### Real-Time State Updates

The MCP Server maintains a persistent WebSocket connection to Home Assistant for real-time updates.

**Features:**
- Auto-connect on startup
- Auto-reconnect with 5-second retry on disconnect
- Subscribes to `state_changed` events
- Updates Redis cache in real-time

**Connection Status:**

Check WebSocket status:
```bash
curl http://localhost:8000/health
```

Look for `home_assistant: "connected"` or `"disconnected"`.

**Event Handling:**

When device states change in Home Assistant:
1. WebSocket receives `state_changed` event
2. Cache is automatically updated
3. Subsequent queries get fresh data instantly

## Redis Caching

### Cache Strategy

Device states are cached in Redis to minimize API calls to Home Assistant.

**Cache Key Format:**
```
ha:state:{entity_id}
```

**Example:**
```
ha:state:light.kitchen_ceiling
```

### Cache Lifecycle

1. **First Query**: Fetch from HA API → Store in cache with TTL
2. **Subsequent Queries**: Return from cache (faster)
3. **State Change via WebSocket**: Update cache immediately
4. **State Change via Service Call**: Invalidate cache → Fetch fresh → Cache new state
5. **TTL Expiration**: Cache cleared after configured TTL (default 30s)

### Cache Invalidation

Cache is invalidated when:
- ✅ **Service called** (turn on/off): Deleted immediately, fresh state fetched
- ✅ **WebSocket event**: Updated in real-time
- ✅ **TTL expires**: Auto-cleared after `HA_CACHE_TTL` seconds

**Post-Control Flow:**
```
1. User: "Turn on kitchen lights"
2. Server calls HA service: light.turn_on
3. Server deletes cache: ha:state:light.kitchen_ceiling
4. Server waits 200ms for HA to update
5. Server fetches fresh state from HA API
6. Server caches new state
7. Response shows correct "on" state
```

### Configuration

Set cache TTL in `.env`:
```bash
HA_CACHE_TTL=30  # seconds
```

**Recommended values:**
- `30` (default): Good balance for most use cases
- `10-15`: Frequently changing sensors
- `60`: Stable devices, reduce API load
- Omit or set to `0`: Disable caching (not recommended)

## Client Shortcuts

The MCP Client has built-in shortcuts that bypass the LLM for common queries, providing instant responses.

### Temperature Queries

**Patterns detected:**
- "What is the temperature?"
- "How hot is it?"
- "Temperature in living room?"

**Action:** Direct call to `ha_get_device_state` with `domain=sensor` and temperature name filter.

### Light Control

**Patterns detected:**
- "Turn on [the] lights"
- "Turn off kitchen lights"
- "Toggle bedroom lights"

**Actions:**
- Extracts action (`turn_on`, `turn_off`, `toggle`)
- Extracts target name (removes "turn", "on", "off", "the", "light", "lights")
- Calls `ha_control_light` directly

### Switch Control

**Patterns detected:**
- "Turn on coffee maker"
- "Turn off fan"
- "Toggle the switch"

**Actions:**
- Extracts action (`turn_on`, `turn_off`, `toggle`)
- Extracts target name (removes action words)
- Calls `ha_control_switch` directly

### Benefits

- ⚡ **Instant response**: No LLM latency
- 🎯 **Accurate parsing**: Regex-based extraction
- 🔧 **Consistent format**: Always uses proper tool format

## API Reference

### HomeAssistantService Class

**Location:** `server.py` lines 83-268

#### Methods

##### `__init__(url: str, token: str, cache_ttl: int = 30)`
Initialize HA service with URL, token, and cache TTL.

##### `async connect() -> None`
Establish WebSocket connection and start maintenance task.

##### `async get_states(domain: Optional[str] = None) -> List[Dict[str, Any]]`
Fetch all entity states, optionally filtered by domain.

##### `async get_state(entity_id: str) -> Optional[Dict[str, Any]]`
Get state of specific entity. Checks cache first, then fetches from API.

##### `async call_service(domain: str, service: str, entity_id: str, **kwargs) -> Dict[str, Any]`
Call Home Assistant service. Automatically invalidates cache for the entity.

##### `async disconnect() -> None`
Close WebSocket connection gracefully.

### Tool Definitions

**Location:** `server.py` lines 296-366

Each tool has a `ToolDefinition` with:
- `name`: Tool identifier
- `description`: Human-readable description for LLM
- `parameters`: JSON Schema for validation

## Examples

### Query All Sensors

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_get_device_state",
    "arguments": {
      "domain": "sensor"
    },
    "session_id": "test"
  }'
```

### Query Temperature Sensors

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_get_device_state",
    "arguments": {
      "domain": "sensor",
      "name_filter": "temperature"
    },
    "session_id": "test"
  }'
```

### Turn On All Kitchen Lights

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_control_light",
    "arguments": {
      "action": "turn_on",
      "name_filter": "kitchen"
    },
    "session_id": "test"
  }'
```

### Turn Off Specific Light

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_control_light",
    "arguments": {
      "action": "turn_off",
      "name_filter": "kitchen above cabinet light"
    },
    "session_id": "test"
  }'
```

### Set Light Brightness

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_control_light",
    "arguments": {
      "action": "turn_on",
      "name_filter": "bedroom",
      "brightness": 128
    },
    "session_id": "test"
  }'
```

### Toggle Switch

```bash
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ha_control_switch",
    "arguments": {
      "action": "toggle",
      "name_filter": "coffee maker"
    },
    "session_id": "test"
  }'
```

### Via Client (with LLM)

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the temperature in the living room?",
    "session_id": "test"
  }'
```

## Troubleshooting

### "Home Assistant not configured" error

**Cause:** `HA_URL` or `HA_TOKEN` not set in `.env`

**Solution:**
1. Check `.env` file exists and has both variables
2. Verify token is correct (regenerate if needed)
3. Restart MCP Server: `npm run dev:server`

### WebSocket connection fails

**Symptoms:**
- Health check shows `home_assistant: "disconnected"`
- Logs show reconnection attempts

**Causes & Solutions:**

**Network issue:**
```bash
# Test connectivity
ping homeassistant.local
curl http://homeassistant.local:8123
```

**Invalid token:**
- Regenerate token in Home Assistant
- Update `HA_TOKEN` in `.env`
- Restart server

**Firewall blocking WebSocket:**
- WebSocket uses same port as HTTP (usually 8123)
- Check firewall allows outbound connections
- REST API will still work without WebSocket

### Device not found

**Symptoms:** "No lights found matching 'xyz'"

**Solutions:**

1. **Check device exists:**
   ```bash
   curl -X POST http://localhost:8000/v1/tools/call \
     -H "Content-Type: application/json" \
     -d '{"tool_name": "ha_get_device_state", "arguments": {"domain": "light"}, "session_id": "test"}'
   ```

2. **Try entity_id directly:**
   ```json
   {
     "tool_name": "ha_control_light",
     "arguments": {
       "action": "turn_on",
       "entity_id": "light.kitchen_ceiling"
     }
   }
   ```

3. **Check friendly name in Home Assistant UI**

### Stale state after control

**Fixed in v2.4.1:** Cache is now properly invalidated after service calls.

**If still seeing issues:**
1. Verify server is v2.4.1+: `curl http://localhost:8000/health`
2. Check Redis is running: `redis-cli ping` (should return `PONG`)
3. Lower `HA_CACHE_TTL` in `.env` to 5-10 seconds
4. Restart server

### Redis connection errors

**Symptoms:** Server starts but logs show Redis errors

**Impact:** Non-critical - server works without caching

**Solutions:**

**Start Redis:**
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis
```

**Verify connection:**
```bash
redis-cli ping  # Should return PONG
```

**Check configuration:**
- Default: `localhost:6379`
- Custom: Set `REDIS_HOST` and `REDIS_PORT` in `.env`

### Permission denied calling service

**Symptoms:** "Failed to call service: 403 Forbidden"

**Cause:** Token lacks permissions

**Solution:**
1. Generate new long-lived token (not temporary)
2. Ensure token is from admin account or account with device permissions
3. Update `.env` with new token
4. Restart server

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current version:** v2.4.1
- Cache invalidation after service calls
- 200ms delay for state updates
- Fresh state fetching post-control

**Previous version:** v2.4.0
- Initial Home Assistant integration
- WebSocket support
- Redis caching
- Smart multi-device control
