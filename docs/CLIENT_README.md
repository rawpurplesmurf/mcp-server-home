# MCP Client - Ollama Integration

A simple FastAPI client that integrates with local Ollama LLM and uses the MCP server tools.

## Setup

1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and install Ollama
2. **Pull a model**: `ollama pull llama3.2` (or your preferred model)
3. **Install dependencies**: `pip install -r client_requirements.txt`
4. **Configure**: Copy `.env.client.example` to `.env.client` and adjust settings
5. **Run**: `uvicorn client:app --port 8001`

## Usage

```bash
# Simple text completion
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?"}'

# Direct tool usage
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you ping google.com?"}'
```

## Configuration

- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: llama3.2)
- `MCP_SERVER_URL`: MCP server URL (default: http://localhost:8000)
- `CLIENT_PORT`: Client server port (default: 8001)