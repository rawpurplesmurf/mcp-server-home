# Voice Quickstart (Wyoming Whisper)

Quick steps to get voice transcription working locally with the rhasspy `wyoming-whisper` container.

Prerequisites
- Docker running on the host machine that will run the Whisper container
- Project virtualenv activated for client: `.venv`

1) Start Wyoming Whisper container on the host (macmini example)

```bash
sudo docker run -d --name whisper -p 10300:10300 -p 10400:10400 rhasspy/wyoming-whisper:latest
sudo docker logs -f whisper
# Wait until you see: INFO:__main__:Ready
```

2) Configure the MCP client

Edit `.env.client` (or `.env.client.example`) and set:

```bash
WHISPER_URL=macmini:10300
```

3) Install Python deps in the client virtualenv

```bash
source .venv/bin/activate
pip install -r client_requirements.txt
```

4) Start services

```bash
# Start client (dev)
npm run dev:client
# Start UI (dev)
npm run dev:ui
```

5) Test from the UI

- Open http://localhost:5173
- Click the 🎤 button, record, stop, and confirm the transcription appears.

If issues
- Check client logs: `tail -f logs/client_*.log`
- Check Whisper container logs on the host: `sudo docker logs whisper`
- Use `scripts/test-wyoming.sh` for a basic connectivity check
