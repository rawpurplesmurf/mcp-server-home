# Voice Input — User Guide

This document explains how to use the voice input feature in the MCP web UI.

How to use
1. Open the Web UI (default: http://localhost:5173).
2. Click the microphone button (🎤). The browser will request microphone permission.
3. Speak clearly. Visual feedback shows recording activity.
4. Click the stop button (⏹️) to finish recording. The UI encodes the audio to a 16kHz mono WAV and uploads it to the `/transcribe` endpoint.
5. If speech is detected, the transcribed text will be placed in the chat input. Edit or send as desired.

Notes and tips
- Microphone permissions: grant access in the prompt, and check browser site settings if permission is denied.
- Speak for at least 1–2 seconds for reliable transcription.
- Background noise reduction: use a headset or quiet room when possible.

Error messages
- "Transcription failed: HTTP error! status: 500" — Server returned an error; open the browser dev console and check the client logs. Also check `logs/client_*.log` on the server for details.
- "No speech detected" — Try again with a longer or clearer recording.

Privacy
- Audio is only uploaded transiently to the configured Whisper service. The client does not persist raw audio files by default.
