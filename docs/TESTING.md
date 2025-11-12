# Testing Guide

This document provides detailed information about the MCP project's testing infrastructure.

## Quick Links

- **[Security Testing](./SECURITY_TESTING.md)** - Bandit security scanning guide
- **[Vulnerability Tracking](./VULNERABILITIES.md)** - Security issue tracking
- **[Changelog](./CHANGELOG.md)** - Version history and test updates
- **[README](../README.md)** - Main project documentation

## Quick Start

```bash
# Run all tests (dependencies + security + pytest + Playwright)
npm test
# Or: bash scripts/run-tests.sh

# Run security scan only
npm run test:security
# Or: bash scripts/security-check.sh
```

## Test Structure

### Backend Tests (pytest)

**Location**: `tests/`

**Files**:
- `conftest.py` - Shared fixtures and pytest configuration
- `test_server.py` - MCP Server tests (port 8000)
- `test_client.py` - MCP Client tests (port 8001)

**Dependencies**: `requirements-test.txt`
- pytest==7.4.3
- pytest-asyncio==0.21.1
- pytest-cov==4.1.0
- httpx==0.25.2
- faker==20.1.0

### Frontend Tests (Playwright)

**Location**: `ui/tests/`

**Files**:
- `ui.spec.js` - End-to-end UI tests
- `../playwright.config.js` - Playwright configuration

**Dependencies**: `@playwright/test@1.40.0`

## Running Tests

### All Tests (Unified Runner)

```bash
npm test
# Or: bash scripts/run-tests.sh
```

**What it does**:
1. Checks and installs test dependencies
2. Runs pytest tests with coverage
3. Runs Playwright UI tests
4. Displays comprehensive summary

**Exit codes**:
- `0` - All tests passed
- `1` - Some tests failed

### Backend Tests Only

```bash
# Install dependencies
pip install -r requirements-test.txt

# Run all backend tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html -v

# Run specific test file
pytest tests/test_server.py -v
pytest tests/test_client.py -v

# Run specific test
pytest tests/test_server.py::TestServerHealth::test_health_endpoint -v
```

### Frontend Tests Only

```bash
cd ui

# Install dependencies
npm install
npx playwright install chromium

# Run all UI tests
npx playwright test

# Run with UI mode (interactive)
npx playwright test --ui

# Run specific test
npx playwright test tests/ui.spec.js

# Run in headed mode (see browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

## Test Coverage

### Backend Coverage

**Server Tests** (`test_server.py`):
- ✅ Health endpoint and Redis status
- ✅ Tools listing endpoint
- ✅ Tool schema validation
- ✅ Network time tool (NTP)
- ✅ Ping tool (localhost, external hosts, missing args)
- ✅ Error handling (unknown tools)
- ✅ LLM generation endpoint
- ✅ **NEW (v2.5.0)**: Home Assistant fuzzy matching tests
  - Punctuation handling ("ellies" → "Ellie's")
  - Switch control with name variations
  - Sensor queries with fuzzy matching

**Client Tests** (`test_client.py`):
- ✅ Health endpoint with Ollama and server status
- ✅ Tools endpoint (proxying server tools)
- ✅ Direct tool testing endpoint
- ✅ Chat endpoint (time queries, ping queries, general)
- ✅ Session management
- ✅ Input validation
- ✅ Root endpoint information
- ✅ **NEW (v2.5.0)**: Feedback system tests
  - Interaction ID in responses
  - Debug information structure
  - Thumbs up feedback (with graceful Redis handling)
  - Thumbs down feedback (with graceful Redis handling)
  - Invalid feedback type validation

**Coverage Reports**:
```bash
# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

### Frontend Coverage

**UI Tests** (`ui.spec.js`):
- ✅ UI rendering and layout
- ✅ Message sending and receiving
- ✅ Tool badge display (get_network_time, ping_host)
- ✅ Loading states and indicators
- ✅ Clear chat functionality
- ✅ Auto-scroll behavior
- ✅ Input validation (empty messages)
- ✅ Button states (disabled during loading)
- ✅ Error handling (server errors)
- ✅ Responsive design (mobile viewport)

**Playwright Reports**:
```bash
# View last test run report
npx playwright show-report

# Report location
ls -la ui/playwright-report/
```

## Prerequisites

### For Backend Tests

**Required services**:
- MCP Server running on port 8000
- MCP Client running on port 8001

**Start services**:
```bash
npm start
# Or: bash scripts/start.sh
```

**Verify services**:
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### For Frontend Tests

**Required**:
- All backend services running (server + client)
- UI will auto-start on port 5173 (managed by Playwright)

**Optional**: Manual UI start
```bash
cd ui
npm run dev
```

## Test Fixtures (Backend)

Located in `tests/conftest.py`:

- **event_loop**: Async event loop for pytest-asyncio
- **server_url**: MCP Server URL (http://localhost:8000)
- **client_url**: MCP Client URL (http://localhost:8001)
- **http_client**: Async HTTP client (httpx.AsyncClient)
- **test_session_id**: Generated session ID for tests

## New Test Cases (v2.5.0)

### Feedback System Tests (`test_client.py`)

**Class**: `TestFeedbackSystem`

**Test: `test_chat_includes_interaction_id`**
- **Purpose**: Verifies every chat response includes unique interaction ID
- **Why**: Interaction IDs are required for submitting feedback (👍/👎)
- **Asserts**: Response contains `interaction_id` field with non-empty value

**Test: `test_chat_includes_debug_info`**
- **Purpose**: Verifies debug information is included in responses
- **Why**: Users need transparency about tool usage and routing decisions
- **Asserts**: 
  - Response contains `debug` field
  - Debug info includes `routing_type` (direct_shortcut, llm_with_tools, llm_only)
  - Debug info has proper structure

**Test: `test_feedback_thumbs_up_without_redis`**
- **Purpose**: Tests thumbs up feedback submission
- **Why**: Positive feedback marks interactions for permanent MySQL storage
- **Asserts**: 
  - Returns 200 on success OR 503 if Redis unavailable (graceful degradation)
  - Response includes success message or service unavailable error

**Test: `test_feedback_thumbs_down_without_redis`**
- **Purpose**: Tests thumbs down feedback submission
- **Why**: Negative feedback removes bad interactions from cache and logs details
- **Asserts**:
  - Returns 200 on success OR 503 if Redis unavailable (graceful degradation)
  - Interaction is deleted from cache on success

**Test: `test_feedback_invalid_type`**
- **Purpose**: Ensures invalid feedback types are rejected
- **Why**: Only "thumbs_up" and "thumbs_down" should be accepted
- **Asserts**: 
  - Returns 400 Bad Request for invalid types
  - Error message explains valid types

**Test: Updated `test_root_endpoint`**
- **Purpose**: Verifies root endpoint documents feedback feature
- **Why**: API discoverability
- **Asserts**: Root response includes "feedback" in available endpoints

### Fuzzy Matching Tests (`test_server.py`)

**Test: `test_ha_fuzzy_matching_punctuation`**
- **Purpose**: Tests light control with punctuation differences in device names
- **Example**: User says "ellies picture room" → matches "Ellie's Picture Room Lamp"
- **Why**: Users don't type apostrophes, hyphens, or other punctuation
- **Asserts**:
  - Tool accepts `name_filter` parameter
  - Returns success OR "not configured" error (graceful if HA unavailable)
  - No parsing/validation errors

**Test: `test_ha_fuzzy_matching_switch`**
- **Purpose**: Tests switch control with name variations
- **Example**: "office fan" → "Office Fan-Switch"
- **Why**: Device names often have extra words like "Switch" or punctuation
- **Asserts**:
  - Tool accepts switch control parameters
  - Handles punctuation/spacing variations
  - Returns appropriate success or error

**Test: `test_ha_fuzzy_matching_sensor`**
- **Purpose**: Tests sensor state queries with fuzzy name matching
- **Example**: "living room" → "Living Room Temperature"
- **Why**: Users use shorthand for device names
- **Asserts**:
  - Tool accepts domain filter and name_filter
  - Fuzzy matching finds devices despite name differences
  - Returns device state or appropriate error

**Design Philosophy**: All fuzzy matching tests handle both:
- **HA configured**: Returns device state or "no devices found"
- **HA not configured**: Returns configuration error
- Both are valid outcomes - tests verify the tool *works*, not that HA is set up

## Test Fixtures (Backend)

## Continuous Integration

The test suite is designed for CI/CD integration:

```bash
# CI-friendly execution
npm test
# Or: bash scripts/run-tests.sh

# Check exit code
echo $?  # 0 = success, 1 = failure
```

**GitHub Actions example**:
```yaml
- name: Run tests
  run: npm test

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./htmlcov/coverage.xml
```

## Debugging Failed Tests

### Backend Tests

```bash
# Verbose output
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l

# Run last failed tests
pytest tests/ --lf
```

### Frontend Tests

```bash
# Debug mode (step through)
npx playwright test --debug

# Headed mode (see browser)
npx playwright test --headed

# Specific browser
npx playwright test --project=chromium

# Screenshot on failure
npx playwright test --screenshot=only-on-failure
```

## Writing New Tests

### Backend Test Template

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_new_feature(http_client: httpx.AsyncClient, server_url: str):
    """Test description"""
    response = await http_client.get(f"{server_url}/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### Frontend Test Template

```javascript
import { test, expect } from '@playwright/test';

test('should do something', async ({ page }) => {
  await page.goto('/');
  
  const element = page.locator('selector');
  await expect(element).toBeVisible();
  await element.click();
  
  await expect(page.locator('.result')).toContainText('expected');
});
```

## Performance

**Typical execution times**:
- Backend tests: ~15-30 seconds
- Frontend tests: ~45-90 seconds (includes browser startup)
- Total: ~1-2 minutes

**Optimization tips**:
- Run tests in parallel: `pytest tests/ -n auto` (requires pytest-xdist)
- Playwright parallel: `npx playwright test --workers=4`
- Skip slow tests during development: `pytest tests/ -m "not slow"`

## Troubleshooting

### "Connection refused" errors

**Issue**: Services not running

**Solution**:
```bash
# Check services
ps aux | grep uvicorn

# Start services
./start.sh

# Wait for services to start
sleep 5

# Verify
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### "Module not found" errors

**Issue**: Test dependencies not installed

**Solution**:
```bash
# Backend
pip install -r requirements-test.txt

# Frontend
cd ui && npm install
```

### Playwright browser issues

**Issue**: Chromium not installed

**Solution**:
```bash
cd ui
npx playwright install chromium
```

### Redis connection errors

**Issue**: Redis not running (optional dependency)

**Note**: Redis is optional. Tests should pass without Redis, but some functionality may be limited.

**Solution** (if Redis is desired):
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Verify
redis-cli ping  # Should return "PONG"
```

## Best Practices

1. **Run tests before committing**: Always run `npm test` before pushing changes
2. **Write tests for new features**: Every new feature should have corresponding tests
3. **Keep tests isolated**: Tests should not depend on each other
4. **Use fixtures**: Leverage shared fixtures in `conftest.py`
5. **Mock external services**: Use mocks for external APIs in unit tests
6. **Test edge cases**: Include error conditions and boundary cases
7. **Keep tests fast**: Optimize slow tests or mark them as `slow`
8. **Document test intentions**: Use clear test names and docstrings

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Playwright documentation](https://playwright.dev/)
- [pytest-asyncio guide](https://pytest-asyncio.readthedocs.io/)
- [httpx documentation](https://www.python-httpx.org/)
