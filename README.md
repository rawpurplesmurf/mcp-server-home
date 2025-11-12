# Model Context Protocol (MCP) Server

A Python FastAPI server implementing a Model Context Protocol (MCP) server focused on network utilities.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Web UI](#web-ui)
- [MCP Client Setup](#mcp-client-setup)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Available Tools](#available-tools)
- [Development](#development)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Testing](#testing)
- [Security](#security)
- [macOS Development Notes](#macos-development-notes)
- [Changelog](#changelog)

## Features

### 🖥️ **MCP Server** (Port 8000)
- **Network Time Tool**: Retrieves accurate time from configurable NTP servers
- **Ping Tool**: Tests network connectivity and latency to specified hosts
- **Home Assistant Integration**: Control smart home devices and query sensor states
  - Query device states (sensors, thermostats, etc.)
  - Control lights with brightness
  - Control switches and outlets
  - Smart multi-device control
  - Real-time state updates via WebSocket
  - Redis caching for device states
- **Redis Caching**: Optional Redis integration for response caching
- **Environment Configuration**: Fully configurable via environment variables

### 🤖 **MCP Client** (Port 8001)
- **Ollama Integration**: Local LLM integration with Qwen2.5:7b-instruct
- **Intelligent Tool Routing**: Automatic detection of time, network, and smart home queries
- **Direct Tool Access**: Manual tool testing endpoints
- **Session Management**: Context-aware conversations
- **Smart Home Shortcuts**: Natural language queries for Home Assistant devices

### 🌐 **Web UI** (Port 5173)
- **Modern Chat Interface**: Sleek, responsive dark-themed chat UI built with React + Vite
- **Real-time Interaction**: Send messages and receive responses from the MCP client instantly
- **Tool Visibility**: Visual badges showing which MCP tools were used in each response
- **Auto-scroll**: Automatically scrolls to the latest messages for seamless conversation flow
- **Session Persistence**: Maintains conversation context throughout your session
- **Mobile Responsive**: Works beautifully on desktop, tablet, and mobile devices
- **👍 👎 Feedback System**: Rate responses to improve the system
  - Thumbs up → Saves interaction permanently (Redis + MySQL)
  - Thumbs down → Removes from cache and logs for analysis
- **Debug View**: Expandable details showing routing decisions, prompts, and tool usage

### 🏠 **Home Assistant Integration**
- **Real-time Updates**: WebSocket connection for instant state changes
- **Smart Device Control**: Natural language commands for lights and switches
- **Multi-Device Support**: Control all lights in a room with one command
- **Precise Control**: Specific device names for individual control
- **Sensor Queries**: Ask about temperature, humidity, and other sensors
- **Caching**: Redis-backed state caching for fast responses
- **Improved Fuzzy Matching**: Handles punctuation differences (e.g., "ellies room" matches "Ellie's Room")

### 💾 **Feedback & Analytics** (Optional)
- **Interaction Logging**: All conversations logged to Redis with 24-hour retention
- **Feedback Tracking**: User ratings (👍/👎) influence caching and storage
- **MySQL Storage**: Long-term storage of approved interactions
- **Analytics Queries**: Insights into tool usage, success rates, and patterns
- **Educational Debug**: See exactly how the system processes each request

> 📖 **New to Model Context Protocol?** See [docs/MCP_EXPLAINED.md](./docs/MCP_EXPLAINED.md) for a comprehensive guide to understanding MCP concepts and how they apply to this project.
> 
> 🔧 **Want to understand the Client Architecture?** See [docs/CLIENT_ARCHITECTURE.md](./docs/CLIENT_ARCHITECTURE.md) for details on how the MCP client integrates with local LLMs.
>
> 🏠 **Setting up Home Assistant?** See [docs/HOME_ASSISTANT.md](./docs/HOME_ASSISTANT.md) for complete Home Assistant integration documentation.
>
> 💾 **Setting up MySQL for feedback?** See [docs/MYSQL_SETUP.md](./docs/MYSQL_SETUP.md) for MySQL integration and analytics setup.
>
> 🤖 **Building AI agents for this project?** See [.github/copilot-instructions.md](./.github/copilot-instructions.md) for AI coding agent guidance.
>
> 🍎 **macOS Developer?** See [docs/MACOS_DEV.md](./docs/MACOS_DEV.md) for platform-specific setup and optimizations.
>
> 🐧 **Linux Developer?** See [docs/LINUX_DEV.md](./docs/LINUX_DEV.md) for Linux/Ubuntu environment setup.
>
> 🪟 **Windows Developer?** See [docs/WINDOWS_DEV.md](./docs/WINDOWS_DEV.md) for Windows 10/11 environment setup.

## Quick Start

### Automated Setup (Recommended)

Use the automated setup script to configure everything:

```bash
git clone <repository-url>
cd model-context-protocol
bash scripts/setup.sh
```

The setup script will:
- ✅ Check Python 3.10+ and Node.js installation
- ✅ Create and activate Python virtual environment
- ✅ Install all Python dependencies (production + testing)
- ✅ Install Node.js dependencies for UI
- ✅ Configure Playwright with Chromium browser
- ✅ Create `.env` and `.env.client` from templates

After setup completes, activate the virtual environment and start services:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
npm start
```

### Manual Setup

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd model-context-protocol
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   # Install all dependencies (Python + Node.js + UI + Playwright)
   npm run install:all
   
   # Or install separately:
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   cd ui && npm install && npx playwright install chromium
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   cp .env.client.example .env.client
   # Edit .env and .env.client with your settings
   ```

4. **Start All Services**:
   ```bash
   npm start
   # Or: bash scripts/start.sh
   ```

5. **Test the MCP Server**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # List available tools
   curl http://localhost:8000/v1/tools/list
   
   # Test network time
   curl -X POST http://localhost:8000/v1/tools/call \
     -H "Content-Type: application/json" \
     -d '{"tool_name": "get_network_time", "arguments": {}, "session_id": "test"}'
   
   # Test ping
   curl -X POST http://localhost:8000/v1/tools/call \
     -H "Content-Type: application/json" \
     -d '{"tool_name": "ping_host", "arguments": {"hostname": "google.com"}, "session_id": "test"}'
   ```

## Web UI

A modern, responsive chat interface is available for easy interaction with the MCP system.

### Quick Start with UI

1. **Start all services** (from project root):
   ```bash
   npm start
   # Or: bash scripts/start.sh
   ```
   This single command starts:
   - MCP Server (port 8000)
   - MCP Client (port 8001)
   - Web UI (port 5173)

2. **Open in browser**: Navigate to `http://localhost:5173`

### UI Features

The Web UI provides an intuitive chat interface with:
- 🎨 **Modern dark theme** - Easy on the eyes for extended use
- 💬 **Real-time chat** - Instant responses from the MCP client
- 🔧 **Tool badges** - Visual indicators showing which tools (NTP time, ping) were used
- 📱 **Fully responsive** - Adapts to any screen size
- ⚡ **Fast & lightweight** - Built with Vite for instant hot-reload during development
- 🗨️ **Clear chat** - Button to clear conversation history
- 🎯 **Auto-scroll** - Always shows the latest messages

### Example Interactions

Try these queries in the UI:
- "What time is it?" → Uses `get_network_time` tool
- "Can you ping google.com?" → Uses `ping_host` tool  
- "What's the temperature in the living room?" → Uses `ha_get_device_state` tool (if Home Assistant configured)
- "Turn on the kitchen lights" → Uses `ha_control_light` tool (if Home Assistant configured)
- "Turn off the coffee maker" → Uses `ha_control_switch` tool (if Home Assistant configured)
- "Hello, what can you help me with?" → General conversation

See [ui/README.md](./ui/README.md) for more UI-specific details.

## MCP Client Setup

The project includes a complete MCP client that integrates with local Ollama models for intelligent tool usage. For detailed architecture information, see [docs/CLIENT_ARCHITECTURE.md](./docs/CLIENT_ARCHITECTURE.md) and [docs/CLIENT_README.md](./docs/CLIENT_README.md).

### Prerequisites
1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and install Ollama
2. **Pull Qwen2.5 Model**: `ollama pull qwen2.5:7b-instruct`

### Client Setup
1. **Configure Client Environment**:
   ```bash
   cp .env.client.example .env.client
   # Edit .env.client with your preferred settings
   ```

2. **Start the Client** (in a new terminal):
   ```bash
   uvicorn client:app --port 8001
   ```

3. **Test the Client**:
   ```bash
   # Health check
   curl http://localhost:8001/health
   
   # Chat with time question
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What time is it?", "session_id": "demo"}'
   
   # Chat with ping question
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Can you ping google.com?", "session_id": "demo"}'
   
   # General conversation
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, what can you help me with?", "session_id": "demo"}'
   ```

## Home Assistant Setup

### Prerequisites
- Home Assistant instance (local or remote)
- Long-lived access token from Home Assistant

### Setup Steps

1. **Generate Access Token in Home Assistant**:
   - Open your Home Assistant instance
   - Click on your profile (bottom left)
   - Scroll to "Security" section
   - Under "Long-Lived Access Tokens", click "Create Token"
   - Give it a name (e.g., "MCP Server")
   - Copy the token (you won't see it again!)

2. **Configure MCP Server**:
   ```bash
   # Edit .env file
   nano .env
   
   # Add Home Assistant configuration:
   HA_URL=http://ha.internal  # or your HA URL
   HA_TOKEN=your_long_lived_token_here
   HA_CACHE_TTL=30  # Cache device states for 30 seconds (optional)
   ```

3. **Restart MCP Server**:
   ```bash
   # If running manually:
   uvicorn server:app --reload --port 8000
   
   # If using npm scripts:
   npm run dev:server
   
   # Or start all services:
   npm start
   ```

4. **Verify Connection**:
   ```bash
   # Check health endpoint
   curl http://localhost:8000/health
   
   # Should show: "home_assistant": "connected"
   ```

### Usage Examples

**Query sensor states**:
```bash
# What's the temperature in the living room?
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the temperature in the living room?", "session_id": "demo"}'

# Get all sensors
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ha_get_device_state", "arguments": {"domain": "sensor"}, "session_id": "demo"}'
```

**Control lights**:
```bash
# Turn on all kitchen lights (broad match - controls multiple)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Turn on the kitchen lights", "session_id": "demo"}'

# Turn off specific light (narrow match - controls one)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Turn off the kitchen above cabinet light", "session_id": "demo"}'

# Set brightness
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ha_control_light", "arguments": {"action": "turn_on", "name_filter": "bedroom", "brightness": 128}, "session_id": "demo"}'
```

**Control switches**:
```bash
# Turn off coffee maker
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Turn off the coffee maker", "session_id": "demo"}'

# Toggle switch
curl -X POST http://localhost:8000/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ha_control_switch", "arguments": {"action": "toggle", "name_filter": "fan"}, "session_id": "demo"}'
```

### Smart Multi-Device Control

The MCP server intelligently determines whether to control one device or multiple:

**Broad queries** (1-2 words) → Controls ALL matching devices:
- "Turn on the kitchen lights" → All lights with "kitchen" in name
- "Turn off bedroom lights" → All bedroom lights
- "Toggle office switches" → All office switches

**Specific queries** (3+ words) → Controls ONE specific device:
- "Turn off the kitchen above cabinet light" → Only that light
- "Turn on the living room reading lamp" → Only that lamp
- "Toggle the bedroom ceiling fan switch" → Only that switch

### Troubleshooting

**"Home Assistant not configured" error**:
- Check that `HA_URL` and `HA_TOKEN` are set in `.env`
- Verify the URL is accessible from your MCP server
- Ensure the access token is valid

**WebSocket connection issues**:
- REST API calls still work without WebSocket
- Check Home Assistant logs for connection errors
- Verify network connectivity to Home Assistant

**Device not found**:
- Check device name in Home Assistant UI
- Try using entity_id directly instead of name_filter
- Query all devices: `{"domain": "light"}` or `{"domain": "switch"}`

## Configuration

The server is configured via environment variables. Copy `.env.example` to `.env` and modify as needed:

### Redis Configuration
- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_PASSWORD`: Redis password (optional)
- `REDIS_DB`: Redis database number (default: 0)

### MySQL Configuration (Optional - for feedback storage)
- `MYSQL_HOST`: MySQL server hostname (default: localhost)
- `MYSQL_PORT`: MySQL server port (default: 3306)
- `MYSQL_DATABASE`: Database name (default: mcp_chat)
- `MYSQL_USER`: MySQL username (default: mcp_user)
- `MYSQL_PASSWORD`: MySQL password (required for MySQL features)
- `MYSQL_POOL_SIZE`: Connection pool size (default: 5)

**Setting up MySQL** (optional - for long-term feedback storage):
1. Install MySQL: `brew install mysql` (macOS) or `sudo apt-get install mysql-server` (Linux)
2. Run setup script: `./scripts/setup-mysql.sh` (interactive) OR manually load schema: `mysql -u root -p < schema.sql`
3. Update `.env` with your MySQL credentials
4. See [docs/MYSQL_SETUP.md](./docs/MYSQL_SETUP.md) for detailed instructions

### NTP Configuration
- `NTP_SERVER`: Primary NTP server (default: pool.ntp.org)
- `NTP_BACKUP_SERVER`: Backup NTP server (default: time.google.com)
- `NTP_TIMEOUT`: NTP request timeout in seconds (default: 5)

### Server Configuration
- `SERVER_PORT`: FastAPI server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

### Home Assistant Configuration
- `HA_URL`: Home Assistant server URL (e.g., http://ha.internal or http://homeassistant.local:8123)
- `HA_TOKEN`: Long-lived access token from Home Assistant (generate in Profile → Security → Long-Lived Access Tokens)
- `HA_CACHE_TTL`: Device state cache TTL in seconds (default: 30)

**Setting up Home Assistant Integration**:
1. Open your Home Assistant instance
2. Go to your Profile → Security
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token", give it a name (e.g., "MCP Server")
5. Copy the token and add it to your `.env` file as `HA_TOKEN`
6. Set `HA_URL` to your Home Assistant URL (e.g., `http://ha.internal`)
7. Restart the MCP server to establish WebSocket connection

The server will:
- Connect via WebSocket to receive real-time state updates
- Cache device states in Redis (if available) with configurable TTL
- Support querying sensors, controlling lights and switches
- Filter devices by domain (sensor, light, switch) and name
- Use improved fuzzy matching (punctuation-agnostic) for device names

### Client Configuration (.env.client)
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: qwen2.5:7b-instruct)
- `MCP_SERVER_URL`: MCP server URL (default: http://localhost:8000)
- `CLIENT_PORT`: Client server port (default: 8001)

See [.env.example](./.env.example) and [.env.client.example](./.env.client.example) for complete configuration templates.

## API Endpoints

### MCP Server (Port 8000)
- `GET /health` - Returns server status and Redis connection status
- `GET /v1/tools/list` - List all available tools
- `POST /v1/tools/call` - Execute a specific tool
- `POST /v1/generate` - LLM generation endpoint with tool reasoning loop

### MCP Client (Port 8001)
- `GET /health` - Returns client, Ollama, and MCP server status
- `GET /tools` - List available tools from MCP server
- `POST /chat` - Chat interface with intelligent tool usage
- `POST /test-tool` - Direct tool testing endpoint
- `POST /feedback` - Submit thumbs up/down feedback for interactions
- `GET /interaction/{session_id}/{interaction_id}` - Retrieve interaction log details

## Available Tools

### Network Tools

#### get_network_time
Retrieves accurate time from NTP servers.
- **Parameters**: None
- **Returns**: UTC timestamp, readable time, offset, and source server

#### ping_host
Tests network connectivity and latency.
- **Parameters**: 
  - `hostname` (required): Hostname or IP address to ping
- **Returns**: Host status, latency, packet loss, and output snippet

### Home Assistant Tools

#### ha_get_device_state
Query state of Home Assistant devices and sensors.
- **Parameters**:
  - `entity_id` (optional): Specific entity to query (e.g., 'sensor.living_room_temperature')
  - `domain` (optional): Filter by domain ('sensor', 'binary_sensor', 'climate', etc.)
  - `name_filter` (optional): Partial name match for device (case-insensitive)
- **Returns**: Device state, attributes, and metadata
- **Example**: Query all temperature sensors in living room

#### ha_control_light
Control Home Assistant lights.
- **Parameters**:
  - `action` (required): 'turn_on', 'turn_off', or 'toggle'
  - `entity_id` (optional): Specific light entity
  - `name_filter` (optional): Find light by room/name (e.g., 'kitchen', 'bedroom')
  - `brightness` (optional): Brightness 0-255 (when turning on)
- **Returns**: New light state and confirmation
- **Example**: "Turn on the living room lights at 50% brightness"

#### ha_control_switch
Control Home Assistant switches.
- **Parameters**:
  - `action` (required): 'turn_on', 'turn_off', or 'toggle'
  - `entity_id` (optional): Specific switch entity
  - `name_filter` (optional): Find switch by name (e.g., 'coffee maker', 'fan')
- **Returns**: New switch state and confirmation
- **Example**: "Turn off the coffee maker"

## Development

The server includes several areas marked for enhancement:
1. Enhanced ping parsing for better latency extraction (see `server.py._execute_ping`)
2. Robust Redis caching with session management (see `server.py.LLMService.generate`)
3. Full LLM integration with tool-use reasoning loop (see `server.py.LLMService.generate`)
4. Redis connection resilience improvements (see `server.py` startup event)

For detailed development workflows and testing, see:
- [test_client.py](./test_client.py) - End-to-end client testing
- [test_config.py](./test_config.py) - Server configuration validation
- [CLIENT_ARCHITECTURE.md](./CLIENT_ARCHITECTURE.md) - Client implementation details
- [.github/copilot-instructions.md](./.github/copilot-instructions.md) - AI agent guidance

## Project Structure

## Project Structure

```
model-context-protocol/
├── server.py             # MCP Server (FastAPI, port 8000)
├── client.py             # MCP Client (Ollama integration, port 8001)
├── requirements.txt      # Python dependencies (server + client)
├── requirements-test.txt # Python test dependencies
├── package.json          # NPM scripts for unified commands
├── .env.example          # Server environment template
├── .env.client.example   # Client environment template
├── docs/                 # Documentation
│   ├── CHANGELOG.md      # Version history
│   ├── CLIENT_ARCHITECTURE.md
│   ├── CLIENT_README.md
│   ├── LINUX_DEV.md
│   ├── MACOS_DEV.md
│   ├── MCP_EXPLAINED.md
│   ├── PROJECT_SUMMARY.md
│   ├── TESTING.md
│   └── WINDOWS_DEV.md
├── scripts/              # Shell scripts
│   ├── start.sh          # Start all services
│   ├── run-tests.sh      # Run all tests
│   └── test.sh           # Quick test suite
├── tests/                # Backend tests (pytest)
│   ├── conftest.py       # Test fixtures
│   ├── test_server.py    # Server tests
│   └── test_client.py    # Client tests
├── ui/                   # Web UI (React + Vite)
│   ├── src/
│   │   ├── App.jsx       # Main chat component
│   │   ├── App.css       # Styles
│   │   └── main.jsx      # Entry point
│   ├── tests/            # UI tests (Playwright)
│   │   └── ui.spec.js
│   ├── playwright.config.js
│   └── package.json
├── test_client.py        # End-to-end client test
└── test_config.py        # Configuration validation
```

## Documentation

This project includes comprehensive documentation for different audiences and purposes:

### 📚 **Core Documentation**
- **[docs/MCP_EXPLAINED.md](./docs/MCP_EXPLAINED.md)** - Comprehensive introduction to Model Context Protocol concepts
- **[docs/CLIENT_ARCHITECTURE.md](./docs/CLIENT_ARCHITECTURE.md)** - Client architecture and LLM integration details
- **[docs/CLIENT_README.md](./docs/CLIENT_README.md)** - Client-specific documentation and usage
- **[docs/HOME_ASSISTANT.md](./docs/HOME_ASSISTANT.md)** - Complete Home Assistant integration guide
- **[docs/PROJECT_SUMMARY.md](./docs/PROJECT_SUMMARY.md)** - High-level project overview and goals

### �️ **Platform-Specific Guides**
- **[docs/MACOS_DEV.md](./docs/MACOS_DEV.md)** - macOS development setup and platform-specific notes
- **[docs/LINUX_DEV.md](./docs/LINUX_DEV.md)** - Linux/Ubuntu environment setup guide
- **[docs/WINDOWS_DEV.md](./docs/WINDOWS_DEV.md)** - Windows 10/11 development environment setup

### 📝 **Configuration & History**
- **[docs/CHANGELOG.md](./docs/CHANGELOG.md)** - Detailed version history and release notes
- **[.env.example](./.env.example)** - Server environment configuration template
- **[.env.client.example](./.env.client.example)** - Client environment configuration template
- **[ui/README.md](./ui/README.md)** - Web UI specific documentation and setup

### 🧪 **Testing & Validation**
- **[docs/TESTING.md](./docs/TESTING.md)** - Comprehensive testing guide
- **[docs/SECURITY_TESTING.md](./docs/SECURITY_TESTING.md)** - Security scanning with Bandit
- **[docs/VULNERABILITIES.md](./docs/VULNERABILITIES.md)** - Security vulnerability tracking
- **[scripts/run-tests.sh](./scripts/run-tests.sh)** - Unified pytest + Playwright + Bandit test runner
- **[scripts/security-check.sh](./scripts/security-check.sh)** - Standalone security scanner
- **[test_client.py](./test_client.py)** - End-to-end client testing script
- **[test_config.py](./test_config.py)** - Server configuration validation script
- **[scripts/test.sh](./scripts/test.sh)** - Comprehensive shell-based test suite

## Testing

The project includes comprehensive automated testing for both backend and frontend:

### Running All Tests

Use the unified test runner to execute all tests:
```bash
npm test
# Or: bash scripts/run-tests.sh
```

This script will:
1. Install test dependencies if needed
2. Run pytest tests for backend (server and client)
3. Run Playwright tests for UI
4. Display a comprehensive summary with pass/fail status

### Backend Testing (pytest)

Run pytest tests separately:
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html -v

# Run specific test files
pytest tests/test_server.py -v
pytest tests/test_client.py -v
```

**Coverage**: Backend tests cover:
- Health endpoints and Redis connectivity
- Tool listing and schema validation
- Network time tool (NTP synchronization)
- Ping tool (localhost, external hosts, error handling)
- LLM generation endpoints
- Chat functionality with session management
- Input validation and error responses

View HTML coverage report: `open htmlcov/index.html`

### Frontend Testing (Playwright)

Run Playwright UI tests separately:
```bash
# From project root
cd ui

# Install Playwright dependencies
npm install
npx playwright install chromium

# Run tests
npx playwright test

# Run tests with UI
npx playwright test --ui

# Run specific test file
npx playwright test tests/ui.spec.js
```

**Coverage**: UI tests cover:
- Chat interface rendering and interactions
- Message sending and receiving
- Tool badge display (get_network_time, ping_host)
- Loading states and error handling
- Clear chat functionality
- Auto-scroll behavior
- Responsive design (mobile/desktop)
- Server error handling

View Playwright report: `npx playwright show-report`

### Prerequisites for Testing

**Backend tests require:**
- MCP Server running on port 8000
- MCP Client running on port 8001
- Start services: `npm start` or `bash scripts/start.sh`

**Frontend tests require:**
- All backend services running
- UI will auto-start on port 5173 (managed by Playwright config)

### Test Organization

```
tests/                    # Backend tests (pytest)
├── conftest.py          # Shared fixtures
├── test_server.py       # MCP server tests
└── test_client.py       # MCP client tests

ui/tests/                # Frontend tests (Playwright)
└── ui.spec.js          # UI end-to-end tests
```

### Security Testing

The project includes automated security scanning using [Bandit](https://bandit.readthedocs.io/), a Python security linter that identifies common security issues.

**Run security scan:**
```bash
# Quick scan
npm run test:security

# Standalone scan with detailed output
bash scripts/security-check.sh
```

**Integrated testing:**
Security scans run automatically as part of the full test suite (`npm test`). The scanner checks for:
- Hardcoded passwords and secrets
- SQL injection vulnerabilities
- Shell injection risks
- Insecure cryptographic usage
- Known dangerous function usage

**Current security status:**
- 🟡 1 HIGH severity finding (MD5 hash - accepted for non-security use)
- 🟡 1 MEDIUM severity finding (shell=True - internal API, limited exposure)
- 🔴 6 LOW severity findings (logging improvements needed)

See **[docs/VULNERABILITIES.md](./docs/VULNERABILITIES.md)** for complete vulnerability tracking and remediation status.

For detailed security testing documentation, including configuration, suppression, and best practices, see **[docs/SECURITY_TESTING.md](./docs/SECURITY_TESTING.md)**.

> **Note**: This project uses Bandit 1.8.7.dev16 (development branch) for Python 3.14 compatibility. Standard releases don't yet support Python 3.14's AST changes.

## Security

### Vulnerability Tracking

All security findings are tracked in **[docs/VULNERABILITIES.md](./docs/VULNERABILITIES.md)** with:
- Severity levels (HIGH, MEDIUM, LOW)
- Current status (TO FIX, ACCEPTED, MITIGATED, RESOLVED)
- Location in codebase
- Remediation plans and timelines
- Risk assessment and justifications

**Current Risk Level: MEDIUM**
- 1 HIGH severity (MD5 hash - accepted for non-security use)
- 1 MEDIUM severity (shell=True - internal API, limited exposure)
- 6 LOW severity (logging improvements needed)

### Security Best Practices

This project follows security best practices:
- ✅ Environment variables for sensitive configuration
- ✅ No hardcoded credentials in source code
- ✅ Input validation with Pydantic models
- ✅ Automated security scanning in CI/CD
- ✅ Regular dependency updates
- ✅ Error isolation (tool failures don't crash server)

### Reporting Security Issues

To report security vulnerabilities:
1. **Non-sensitive findings**: File a GitHub issue with [SECURITY] tag
2. **Critical/sensitive issues**: Contact maintainers directly

All security reports are reviewed within 48 hours.

---

## macOS Development Notes

This project was developed and tested on macOS. For platform-specific development information, including setup, configuration, and optimization tips for macOS developers, please see our [macOS Development Guide](./MACOS_DEV.md).

> 🍎 **macOS Users**: The project includes specific optimizations and configurations for macOS development environments, including proper handling of network interfaces, NTP server selection, and Ollama integration.

## Changelog

### v2.0.0 - Complete MCP Client Integration (November 7, 2025)

#### 🤖 **MCP Client Implementation**
- **Ollama Integration**: Full integration with local Ollama LLM server
- **Qwen2.5:7b-instruct Model**: Optimized for reliable tool usage patterns
- **Intelligent Tool Routing**: Automatic detection of time and network queries
- **Direct Tool Testing**: `/test-tool` endpoint for manual tool execution
- **Session Management**: Context-aware conversation handling
- **Health Monitoring**: Complete system status across all components

#### 🧠 **Smart Query Processing**
- **Time Query Detection**: Automatic triggering of `get_network_time` tool
- **Network Query Detection**: Automatic triggering of `ping_host` tool
- **Hostname Extraction**: Intelligent parsing of hostnames from user queries
- **Fallback Responses**: Graceful handling of non-tool-related queries

#### 🔧 **Client Architecture**
- **Async Operations**: Non-blocking client-server communication
- **Error Handling**: Comprehensive error management across all operations
- **Configuration Management**: Separate client environment configuration
- **Multi-Model Support**: Easy switching between Ollama models

#### 📊 **Dual-Server Architecture**
- **MCP Server**: Port 8000 - Tool execution and caching
- **MCP Client**: Port 8001 - LLM integration and chat interface
- **Independent Operation**: Each server can run and be tested independently
- **Seamless Communication**: Automatic tool discovery and execution

#### 🧪 **Enhanced Testing**
- **Client Test Suite**: `test_client.py` for end-to-end validation
- **Live Demonstrations**: Working examples of all functionality
- **Model Validation**: Tested with multiple Ollama models
- **Performance Metrics**: Response time and accuracy measurements

### v1.0.0 - Initial MCP Server Release (November 7, 2025)

#### 🚀 **Core Features**
- **FastAPI Server**: Full async/await FastAPI implementation with automatic OpenAPI documentation
- **Network Tools Focus**: Specialized MCP server for network utilities only
- **Redis Integration**: Async Redis client with connection pooling and graceful fallback
- **Environment Configuration**: Complete .env-based configuration system

#### 🔧 **Available Tools**
- **`get_network_time`**: NTP-based network time synchronization
  - Configurable NTP servers (primary/backup)
  - Millisecond precision with offset calculation
  - Graceful fallback to system time
  - Configurable timeout settings
- **`ping_host`**: Network connectivity and latency testing
  - Cross-platform ping implementation (Windows/Linux/macOS)
  - Packet loss detection and reporting
  - Latency measurement and parsing
  - Configurable ping count

#### 🏗️ **Architecture**
- **Pydantic Schemas**: Type-safe request/response models
- **Service Layer**: Clean separation of concerns with ToolService and LLMService
- **Async Operations**: Non-blocking operations for all network calls
- **Error Handling**: Comprehensive error handling with detailed error responses

#### 📊 **API Endpoints**
- `GET /health` - Server and Redis connection status
- `GET /v1/tools/list` - List available tools with schema
- `POST /v1/tools/call` - Execute tools with arguments
- `POST /v1/generate` - LLM integration endpoint (with mock implementation)

#### ⚙️ **Configuration System**
- **Redis Configuration**: Host, port, password, database selection
- **NTP Configuration**: Primary/backup servers, timeout settings
- **Server Configuration**: Port, logging level
- **Environment Files**: `.env` support with `.env.example` template
- **Git Integration**: Proper `.gitignore` for sensitive configuration

#### 🧪 **Testing & Validation**
- **Health Checks**: Redis connectivity validation
- **Configuration Testing**: `test_config.py` script for end-to-end validation
- **API Testing**: cURL examples and automated test script
- **Cross-platform Support**: Tested on macOS, designed for Linux/Windows compatibility

#### 📚 **Documentation**
- **Comprehensive README**: Setup, configuration, and usage instructions
- **Environment Templates**: `.env.example` with detailed comments
- **API Examples**: Complete cURL examples for all endpoints
- **Configuration Guide**: Detailed explanation of all environment variables

#### 🔒 **Security & Best Practices**
- **Environment Variables**: Sensitive configuration excluded from version control
- **Type Safety**: Full Pydantic validation for all inputs/outputs
- **Error Isolation**: Tools failures don't crash the server
- **Resource Management**: Proper async resource cleanup

#### 📦 **Dependencies**
- `fastapi` - Modern web framework
- `uvicorn[standard]` - ASGI server with performance optimizations
- `pydantic` - Data validation and serialization
- `redis[asyncio]` - Async Redis client
- `ntplib` - Network Time Protocol client
- `python-dotenv` - Environment variable management
- `requests` - HTTP client for testing

#### 🎯 **Future Enhancements** (Marked for Implementation)
- **Task 1**: Enhanced ping parsing with robust latency extraction
- **Task 2**: Advanced Redis caching with session-based context management
- **Task 3**: Full LLM integration with tool-use reasoning loop
- **Task 4**: Redis connection resilience and connection pooling improvements

We are going to build an MCP server we can got to do things on our behalf with an LLM model.