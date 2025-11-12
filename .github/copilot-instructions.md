## Model Context Protocol (MCP) — Copilot instructions

Purpose: provide concise, actionable knowledge so an AI coding agent can be immediately productive in this repo.

### 1. Big Picture Architecture
**Three-tier system**: MCP Server (port 8000) → MCP Client (port 8001) → Web UI (port 5173)

- **server.py** (MCP Server): FastAPI server exposing network tools (`get_network_time`, `ping_host`) and Home Assistant tools (`ha_get_device_state`, `ha_control_light`, `ha_control_switch`) via standard MCP endpoints (`/v1/tools/list`, `/v1/tools/call`). Uses async operations, optional Redis caching, WebSocket connection to Home Assistant, and service-layer pattern (`ToolService`, `LLMService`, `HomeAssistantService`).
- **client.py** (MCP Client): Ollama integration layer with intelligent routing. Direct shortcuts for common queries (e.g., "time" → `get_network_time`, "temperature" → `ha_get_device_state`, "turn on light" → `ha_control_light`), otherwise uses LLM to parse intent and emit `USE_TOOL:tool_name:{json}` directives.
- **ui/** (React + Vite): Modern chat interface at port 5173. Calls `/chat` endpoint on client, displays tool usage badges, maintains session context.

**Data flow**: User message → UI → Client `/chat` → Ollama LLM → Tool detection → Server `/v1/tools/call` → Tool execution (Network/Home Assistant) → Response chain back to UI.

**Home Assistant Integration**: WebSocket connection established at startup subscribes to `state_changed` events. Device states cached in Redis with configurable TTL (default 30s). REST API used for service calls (lights, switches) and state queries.

**Feedback & Analytics System**: Two-tier storage with Redis (24hr cache) + MySQL (permanent storage). UI includes 👍/👎 buttons on responses. Thumbs up saves interaction permanently in both Redis and MySQL. Thumbs down immediately deletes from Redis and logs to MySQL negative_feedback table for analysis. Schema includes three tables with analytics views for tool usage patterns.

### 2. How LLM ↔ Tools Work (Critical Pattern)
Client orchestration in `client.py.OllamaClient`:
- **Direct routing** (shortcuts): `_is_time_query()` and `_is_ping_query()` detect patterns like "what time" or "ping X.com" and call tools immediately without LLM.
- **LLM-guided usage**: For other queries, `_build_prompt()` creates system prompt instructing Ollama to emit exact format:
  ```
  USE_TOOL:get_network_time:{}
  USE_TOOL:ping_host:{"hostname": "google.com"}
  ```
- **Parsing & execution**: `_handle_tool_usage()` parses these lines with regex, extracts tool name + JSON args, calls `MCPClient.call_tool()` → server.
- **Server-side LLM**: `LLMService.generate()` is a stub (mock response). Real LLM interaction happens client-side only. Server caching pattern: `cache:prompt:{session_id}:{hash(prompt)}` (not actively used since LLM is client-side).

### 3. Essential Developer Workflows

**Quick start (all services)**:
```bash
bash scripts/setup.sh      # First-time: venv, deps, config files
source .venv/bin/activate  # Activate venv
npm start                  # Starts server + client + UI with logs
```

**Individual services** (for debugging):
```bash
npm run dev:server   # Server only (port 8000, auto-reload)
npm run dev:client   # Client only (port 8001, auto-reload)
npm run dev:ui       # UI only (port 5173, Vite HMR)
```

**Testing** (requires services running):
```bash
npm test             # Runs both pytest (backend) + Playwright (UI)
npm run test:backend # pytest with coverage → htmlcov/
npm run test:ui      # Playwright UI tests → ui/playwright-report/
```

**Test structure**:
- `tests/conftest.py`: pytest fixtures (`http_client`, `server_url`, `client_url`, `test_session_id`)
- `tests/test_server.py`: Server endpoints, tool schemas, NTP/ping execution
- `tests/test_client.py`: Client endpoints, Ollama integration, tool routing
- `ui/tests/ui.spec.js`: Playwright end-to-end chat flow

**Health checks**:
```bash
curl http://localhost:8000/health  # Server: status, redis, service
curl http://localhost:8001/health  # Client: status, ollama, mcp_server, model
```

### 4. Project-Specific Patterns & Gotchas

**Optional dependencies**:
- **Redis**: Server starts without Redis if unavailable (`redis_client = None`). No caching, but tools work. Check `server.py` startup event. Home Assistant state caching disabled without Redis.
- **ntplib**: If missing, `get_network_time` falls back to `datetime.now(timezone.utc)` system time. Check `NTP_CLIENT_AVAILABLE` flag.
- **Home Assistant**: If `HA_TOKEN` not set, HA tools return configuration error. WebSocket connection optional - REST API still works without it.

**Cross-platform ping**:
- `server.py._execute_ping()` uses `subprocess.run(['ping', ...])` with platform-specific parsing (Windows vs Unix output differs).
- Regex patterns: `time=(\d+\.?\d*)` for latency, packet stats for loss.
- **When modifying**: Test on target platforms; output format is brittle.

**Tool definition contract**:
- `ToolService.TOOLS` dict is source of truth for schemas.
- **Adding tools**: (1) Add to `TOOLS` dict with `ToolDefinition`, (2) implement in `ToolService.call_tool()`, (3) update `client.py._build_prompt()` system message, (4) optionally add shortcut to `client.py._check_direct_tool_usage()`.
- **Client shortcuts**: Update `_is_*_query()` methods or add new keyword detection in `_check_direct_tool_usage()` for direct routing patterns.
- **Home Assistant tools**: Use `domain` parameter to filter device types (sensor, light, switch, climate), `name_filter` for fuzzy name matching (case-insensitive partial match on friendly_name or entity_id).

**Environment config** (two files):
- `.env` (server): `REDIS_*`, `NTP_*`, `SERVER_PORT`, `HA_URL`, `HA_TOKEN`, `HA_CACHE_TTL`
- `.env.client` (client): `OLLAMA_URL`, `OLLAMA_MODEL`, `MCP_SERVER_URL`, `CLIENT_PORT`, `LOG_LEVEL`, `MYSQL_*`
- Default model: `qwen2.5:7b-instruct` (configurable, must be in Ollama)
- **HA setup**: Set `HA_URL=http://ha.internal` and generate long-lived access token in Home Assistant (Profile → Security → Create Token)
- **MySQL setup** (optional): Run `./scripts/setup-mysql.sh` for interactive setup or manually load `schema.sql`. Set `MYSQL_*` vars in `.env.client`

**CORS setup**:
- Client has CORS middleware for UI origins: `http://localhost:5173`, `http://127.0.0.1:5173`
- Server has no CORS (client-to-server is backend-to-backend)

### 5. Where to Edit Behavior Safely

**Add new tool**:
1. `server.py.ToolService.TOOLS`: Add `ToolDefinition` with name, description, parameter schema
2. `server.py.ToolService.call_tool()`: Add case in if/elif chain, implement `async def _execute_*` method
3. `client.py.OllamaClient._build_prompt()`: Document new tool in system prompt
4. (Optional) Add shortcut: `client.py._check_direct_tool_usage()` for direct routing

**Example - Home Assistant tools**:
- `ha_get_device_state`: Query sensor states with domain filter (sensor, climate, etc.)
- `ha_control_light`: Control lights with action (turn_on/off/toggle), optional brightness
- `ha_control_switch`: Control switches with action (turn_on/off/toggle)
- All support `name_filter` for fuzzy name matching (e.g., "living room" matches "Light Living Room")

**Change LLM behavior**:
- **Client prompts**: `client.py.OllamaClient._build_prompt()` - modify system instructions, keep `USE_TOOL:` format
- **Server stub**: `server.py.LLMService.generate()` (currently unused mock)
- **Model selection**: Change `OLLAMA_MODEL` in `.env.client`, ensure model is pulled in Ollama

**UI customization**:
- `ui/src/App.jsx`: React component, chat state, message rendering, feedback buttons (`submitFeedback()`)
- `ui/src/App.css`: Styling (dark theme, chat bubbles, tool badges, feedback buttons)
- API endpoint: hardcoded `http://localhost:8001/chat` in `App.jsx.sendMessage()`

**Feedback system**:
- **Client endpoints**: `/feedback` POST endpoint in `client.py` handles thumbs up/down
- **Storage logic**: `save_interaction_to_mysql()` and `save_negative_feedback_to_mysql()` in `client.py`
- **Redis keys**: `interaction:{session_id}:{interaction_id}`, `feedback:thumbs_up:{session_id}`, `feedback:thumbs_down:{session_id}`
- **MySQL schema**: `schema.sql` defines three tables + analytics views. Run `./scripts/setup-mysql.sh` for setup

### 6. Testing Patterns & Examples

**Pytest fixtures** (from `conftest.py`):
```python
async def test_example(http_client, server_url, test_session_id):
    response = await http_client.post(
        f"{server_url}/v1/tools/call",
        json={"tool_name": "ping_host", "arguments": {"hostname": "1.1.1.1"}, "session_id": test_session_id}
    )
    assert response.status_code == 200
```

**Playwright UI test** (`ui/tests/ui.spec.js`):
```javascript
await page.goto('http://localhost:5173');
await page.fill('[placeholder="Type your message..."]', 'What time is it?');
await page.click('button[type="submit"]');
await expect(page.locator('.message.assistant')).toContainText('time', { timeout: 10000 });
```

**Manual cURL tests**:
```bash
# Test tool call
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_network_time", "arguments": {}, "session_id": "test"}'

# Test client chat
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?", "session_id": "test"}'
```

### 7. Reference Files & Documentation
- **README.md**: Complete setup, API examples, feature overview
- **docs/MCP_EXPLAINED.md**: MCP protocol concepts, standards, this project's implementation
- **docs/CLIENT_ARCHITECTURE.md**: Client design, Ollama integration patterns
- **docs/MYSQL_SETUP.md**: MySQL integration setup and analytics guide
- **docs/{MACOS,LINUX,WINDOWS}_DEV.md**: Platform-specific setup guides
- **server.py**: Tool implementations (lines 74-195), schemas (lines 45-65), endpoints (lines 307-316)
- **client.py**: Ollama client (lines 94-270), tool routing (lines 163-248), prompt building (~line 100+)
- **scripts/**: `setup.sh` (initial install), `start.sh` (run all services), `run-tests.sh` (test runner), `setup-mysql.sh` (MySQL setup)
- **.env.example / .env.client.example**: Configuration templates with all options
- **schema.sql**: MySQL database schema with analytics views

### 8. Common Tasks Quick Reference

**Check if services are running**:
```bash
lsof -i :8000  # MCP Server
lsof -i :8001  # MCP Client  
lsof -i :5173  # Web UI
```

**View logs** (when using `scripts/start.sh`):
```bash
tail -f logs/server_*.log
tail -f logs/client_*.log
tail -f logs/ui_*.log
```

**Debugging tool execution**:
- Server: Check `ToolService.call_tool()` for tool dispatch logic
- Client: Check `OllamaClient._handle_tool_usage()` for parsing, `process_message()` for flow
- Enable verbose logging: Set `LOG_LEVEL=DEBUG` in `.env.client`

**Common errors**:
- "Ollama not available": Ensure Ollama is running (`ollama serve`), check `OLLAMA_URL` in `.env.client`
- "MCP Server unreachable": Check server is running on port 8000, verify `MCP_SERVER_URL` in `.env.client`
- "Model not found": Pull model in Ollama first (`ollama pull qwen2.5:7b-instruct`)

---

**Questions or unclear areas?** Ask about: cache key formats, error response shapes, test assertion patterns, prompt engineering strategies, or platform-specific tool behavior.
