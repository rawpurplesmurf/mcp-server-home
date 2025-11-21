## Voice Implementation (Wyoming Whisper)

This document describes the current voice transcription implementation used by the MCP client and web UI. The project now uses the Wyoming protocol (rhasspy/wyoming-whisper) for streaming speech-to-text and a browser-side WAV encoder so the server receives 16kHz, 16-bit, mono WAV audio.

Key points
- Client UI records audio in the browser using AudioContext (16kHz mono).
- A small WAV encoder (ui/src/wavEncoder.js) packages raw PCM into a standard WAV file with correct headers.
- The UI sends the WAV file to the MCP client `/transcribe` endpoint as multipart/form-data.
- The MCP client uses the `wyoming` Python library and `AsyncTcpClient` to stream audio to a Wyoming Whisper container over TCP (default port 10300).

Files changed/added for voice
- `ui/src/App.jsx` — replaced MediaRecorder-based recording with AudioContext-based capture and uses `WavEncoder` to produce 16kHz mono WAVs.
- `ui/src/wavEncoder.js` — small, dependency-free WAV encoder used by the browser.
- `client.py` — updated `/transcribe` endpoint to use Wyoming `AsyncTcpClient` and stream `AudioStart` / `AudioChunk` / `AudioStop` events and read `Transcript` responses.
- `client_requirements.txt` — ensured `wyoming` and `python-multipart` are listed.
- `scripts/test-wyoming.sh` — convenience script to test TCP connectivity and simple Describe/Info handshake.

Design contract
- Inputs: multipart/form-data `file` containing a WAV (16kHz, 16-bit, mono)
- Outputs: JSON {"text": "...", "status": "success"} or {"text":"","status":"success","warning":"..."}
- Error modes: 503 when service unavailable; 504 on timeout; success with empty text when no speech detected.

Edge cases and notes
- Browsers do not produce perfectly-sized frames — audio is concatenated then encoded into WAV before upload.
- Wyoming expects PCM/WAV. The preferred approach is client-side WAV encoding. Server-side conversion is supported as a fallback but is not the default.
- If you prefer server-side conversion, see `docs/WYOMING_WHISPER.md` for pydub/ffmpeg notes.

Troubleshooting
- If you receive an empty transcript: verify browser recorded audio (UI shows visual feedback), verify `WHISPER_URL` in `.env.client`, and check `docker logs whisper` on the host.
- Ensure `wyoming` and `python-multipart` are installed in the client virtualenv: `.venv/bin/pip install wyoming python-multipart`

Verification
- Unit tests for the `/transcribe` endpoint use mocked audio and are in `tests/test_client.py` (transcribe endpoint test).
- Manual test: Use the in-repo `scripts/test-wyoming.sh` after setting `WHISPER_URL` and activating your `.venv`.
