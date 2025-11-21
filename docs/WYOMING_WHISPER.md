# Wyoming Whisper Integration

## Overview

This MCP server now supports the **Wyoming protocol** for voice transcription using `rhasspy/wyoming-whisper` Docker containers. Wyoming is a peer-to-peer protocol used by Home Assistant and Rhasspy for voice services.

## Your Setup

Based on your configuration:

```bash
# Docker container running on macmini
Container: rhasspy/wyoming-whisper:latest
Ports: 10300 (Wyoming protocol), 10400
Host: macmini
Model: sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
```

## Configuration

### .env.client

```bash
# Wyoming Whisper Configuration
WHISPER_URL=macmini:10300
```

Format options:
- `host:port` (recommended): `macmini:10300`
- `ip:port`: `192.168.1.100:10300`
- `http://host:port` (http:// stripped): `http://macmini:10300`

### Verify Container

```bash
# On macmini host
sudo docker ps | grep whisper
sudo docker logs whisper

# Should show:
# INFO:__main__:Ready
```

## How It Works

1. **Browser** records audio using AudioContext at 16kHz, mono and encodes it to WAV in the browser.
2. **UI** uploads the WAV (`multipart/form-data`) to the MCP client's `/transcribe` endpoint.
3. **Client** opens a TCP connection to the Wyoming Whisper container and streams audio using the Wyoming event protocol.
4. **Wyoming Protocol Exchange**:
   - Send `Transcribe` event (language: en)
   - Send `AudioStart` event (rate=16000, width=2, channels=1)
   - Stream audio in chunks via `AudioChunk` events
   - Send `AudioStop` event
   - Receive `Transcript` event with text
5. **Client** returns the transcribed text to the UI as JSON.

## Dependencies

```bash
# Python library (installed automatically)
pip install wyoming
```

## Testing Connection

```bash
# From your development machine
source .venv/bin/activate
python3 << 'EOF'
import asyncio
from wyoming.client import AsyncTcpClient

async def test():
    client = AsyncTcpClient('macmini', 10300)
    await client.connect()
    print('✓ Connected to Wyoming Whisper')
    await client.disconnect()

asyncio.run(test())
EOF
```

Expected output:
```
✓ Connected to Wyoming Whisper
```

## Troubleshooting

### Connection Refused

Symptom: `Whisper service unavailable at <host>:10300`

Solutions:
1. Verify container is running on the host:
   ```bash
   sudo docker ps | grep whisper
   ```

2. Check port mapping (should map 10300):
   ```bash
   docker ps --format '{{.Names}} {{.Ports}}' | grep whisper
   ```

3. Test network connectivity from the client machine:
   ```bash
   nc -zv <host> 10300
   # or
   telnet <host> 10300
   ```

4. Check host firewall rules and allow port 10300/tcp if needed.

### Empty or Missing Transcript

Symptom: You receive a transcript event but the text is empty, or the `/transcribe` endpoint returns an empty result.

Likely causes and checks:
- The browser recorded an empty buffer (verify UI recording indicator).
- Audio was too short (record at least 1–2s).
- The client sent audio in an unsupported format. The preferred approach for this project is to encode 16kHz, 16-bit, mono WAV in the browser (see `ui/src/wavEncoder.js`).
- The model is still loading on the Whisper container — check `sudo docker logs whisper` for model download or initialization messages.

Quick checks:
- Confirm the UI sent a WAV file (browser devtools → Network → `/transcribe`).
- Inspect client logs (`logs/client_*.log`) for "Received audio" debug lines which include detected headers and sizes.

Fallbacks:
- Server-side conversion using `pydub` + `ffmpeg` is supported as a fallback, but **client-side WAV encoding is the recommended path** to avoid server CPU cost and avoid needing ffmpeg on the server.

### Timeout (504)

**Symptom**: Transcription takes too long

**Solutions**:
1. Use faster Whisper model (tiny, base instead of medium/large)
2. Reduce recording length
3. Increase timeout in client.py

### Import Error

**Symptom**: `Wyoming library not installed`

**Solution**:
```bash
source .venv/bin/activate
pip install wyoming
npm run dev:client  # Restart client
```

## Wyoming vs HTTP Whisper

| Feature | Wyoming | HTTP API |
|---------|---------|----------|
| Protocol | TCP/Event-based | REST/HTTP |
| Container | rhasspy/wyoming-whisper | onerahmet/openai-whisper-asr-webservice |
| Port | 10300 | 9000 |
| Streaming | Yes (chunked) | No (upload whole file) |
| Language | Per-request | Server default |
| Home Assistant | Native support | Requires wrapper |

## Advanced: Notes on audio formats

Wyoming expects **16kHz, 16-bit, mono PCM**. This project implements client-side WAV encoding to ensure compatibility. If you must perform server-side conversion, use `pydub` + `ffmpeg` on the client virtualenv, but note the additional dependencies and CPU cost.


## References

- **Wyoming Protocol**: https://github.com/rhasspy/wyoming
- **Wyoming Whisper**: https://github.com/rhasspy/wyoming-faster-whisper
- **Docker Image**: https://hub.docker.com/r/rhasspy/wyoming-whisper
- **Home Assistant Integration**: https://www.home-assistant.io/integrations/wyoming/

## Summary

✅ **Implementation Complete**
- Wyoming protocol support added to `client.py`
- TCP connection to your Wyoming Whisper on macmini:10300
- Audio streaming via Wyoming event protocol
- Graceful fallback if Wyoming library not installed
- Configuration documented in `.env.client.example`

🎤 **Ready to use** - restart client and test voice input in UI!
