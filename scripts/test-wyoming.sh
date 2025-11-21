#!/bin/bash
# Test Wyoming Whisper connection

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🎤 Testing Wyoming Whisper Connection"
echo ""

# Load environment
if [ ! -f .env.client ]; then
    echo -e "${RED}✗ .env.client not found${NC}"
    exit 1
fi

source .env.client

# Extract host and port from WHISPER_URL
WHISPER_HOST=$(echo "$WHISPER_URL" | sed 's/http:\/\///' | sed 's/https:\/\///' | cut -d':' -f1)
WHISPER_PORT=$(echo "$WHISPER_URL" | sed 's/http:\/\///' | sed 's/https:\/\///' | cut -d':' -f2)

if [ -z "$WHISPER_PORT" ]; then
    WHISPER_PORT=10300
fi

echo "Configuration:"
echo "  Host: $WHISPER_HOST"
echo "  Port: $WHISPER_PORT"
echo ""

# Check network connectivity
echo "1. Testing network connectivity..."
if command -v nc &> /dev/null; then
    if nc -zv "$WHISPER_HOST" "$WHISPER_PORT" 2>&1 | grep -q "succeeded"; then
        echo -e "   ${GREEN}✓ Network connection OK${NC}"
    else
        echo -e "   ${RED}✗ Cannot connect to $WHISPER_HOST:$WHISPER_PORT${NC}"
        echo "   Check that:"
        echo "   - Docker container is running: sudo docker ps | grep whisper"
        echo "   - Port is accessible: telnet $WHISPER_HOST $WHISPER_PORT"
        exit 1
    fi
else
    echo -e "   ${YELLOW}⚠ netcat (nc) not found, skipping network test${NC}"
fi
echo ""

# Check Wyoming library
echo "2. Checking Wyoming library..."
if python3 -c "import wyoming" 2>/dev/null; then
    echo -e "   ${GREEN}✓ Wyoming library installed${NC}"
else
    echo -e "   ${RED}✗ Wyoming library not installed${NC}"
    echo "   Install with: pip install wyoming"
    exit 1
fi
echo ""

# Test Wyoming protocol connection
echo "3. Testing Wyoming protocol connection..."
python3 << EOF
import asyncio
from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info
import sys

async def test():
    try:
        client = AsyncTcpClient('$WHISPER_HOST', $WHISPER_PORT)
        await client.connect()
        
        # Request service info
        await client.write_event(Describe().event())
        
        # Read response
        timeout_count = 0
        while timeout_count < 10:
            try:
                event = await asyncio.wait_for(client.read_event(), timeout=1.0)
                if event is None:
                    break
                if Info.is_type(event.type):
                    info = Info.from_event(event)
                    print(f'   \033[0;32m✓ Connected successfully\033[0m')
                    print(f'     Service: {info.name}')
                    print(f'     Version: {info.version}')
                    if info.asr:
                        for asr in info.asr:
                            print(f'     Model: {asr.name}')
                            if asr.languages:
                                print(f'     Languages: {", ".join(asr.languages[:5])}')
                    await client.disconnect()
                    return 0
            except asyncio.TimeoutError:
                timeout_count += 1
                continue
        
        print('   \033[1;33m⚠ Connected but no service info received\033[0m')
        await client.disconnect()
        return 0
        
    except ConnectionRefusedError:
        print(f'   \033[0;31m✗ Connection refused\033[0m')
        print(f'   Check Docker container: sudo docker ps | grep whisper')
        return 1
    except Exception as e:
        print(f'   \033[0;31m✗ Connection failed: {e}\033[0m')
        return 1

sys.exit(asyncio.run(test()))
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start the client: npm run dev:client"
    echo "  2. Start the UI: npm run dev:ui"
    echo "  3. Click the 🎤 button to test voice input"
else
    echo ""
    echo -e "${RED}❌ Tests failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Verify container: sudo docker ps | grep whisper"
    echo "  - Check logs: sudo docker logs whisper"
    echo "  - Test manually: telnet $WHISPER_HOST $WHISPER_PORT"
    exit 1
fi
