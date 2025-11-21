# Docker Deployment Guide

This directory contains Docker configurations for running the MCP Server, Client, and Web UI in containers.

## Quick Start

### Option 1: Simple Container (Recommended)
Run just the MCP application, connecting to external services:

```bash
# Build and run the container
docker build -t mcp-server .
docker run -p 8000:8000 -p 8001:8001 -p 5173:5173 mcp-server

# Or use docker-compose
docker-compose -f docker-compose.simple.yml up --build
```

### Option 2: Full Stack with Dependencies
Run MCP app with Redis and MySQL included:

```bash
# Set required environment variables
export MYSQL_PASSWORD=your_secure_password
export HA_TOKEN=your_ha_token  # Optional
export OLLAMA_URL=http://host.docker.internal:11434  # Optional

# Start all services
docker-compose up --build
```

## Access Points

Once running, access the services at:
- **Web UI**: http://localhost:5173
- **MCP Client**: http://localhost:8001  
- **MCP Server**: http://localhost:8000

## Configuration

### Environment Variables

Set these environment variables to configure external service connections:

**Ollama (LLM)**:
```bash
export OLLAMA_URL=http://host.docker.internal:11434  # Default for Docker Desktop
# Or for Linux: export OLLAMA_URL=http://172.17.0.1:11434
```

**Home Assistant** (optional):
```bash
export HA_URL=http://your-ha-server:8123
export HA_TOKEN=your_long_lived_access_token
```

**MySQL** (for feedback system):
```bash
export MYSQL_PASSWORD=your_secure_password
export MYSQL_ROOT_PASSWORD=your_root_password
```

### Configuration Files

The container creates default `.env` and `.env.client` files from templates. To use custom configuration:

1. Create your own `.env` and `.env.client` files
2. Mount them into the container:
   ```bash
   docker run -v $(pwd)/.env:/app/.env -v $(pwd)/.env.client:/app/.env.client -p 8000:8000 -p 8001:8001 -p 5173:5173 mcp-server
   ```

## Docker Compose Options

### Simple Deployment (`docker-compose.simple.yml`)
- Only runs the MCP application
- Connects to external Redis, MySQL, Ollama, Home Assistant
- Best for development or when you have existing services

### Full Stack (`docker-compose.yml`)  
- Includes Redis and MySQL containers
- Sets up networking between services
- Includes volume persistence for data
- Best for complete isolated deployment

## Prerequisites

### For Ollama Integration
You need Ollama running on your host machine:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull the default model
ollama pull qwen2.5:7b-instruct
```

### For Home Assistant Integration
- Home Assistant instance running and accessible
- Long-lived access token generated in HA UI

### Network Configuration

All services are configured to bind to `0.0.0.0` (all network interfaces) to ensure they're accessible outside the container:
- **MCP Server**: `uvicorn server:app --host 0.0.0.0 --port 8000`
- **MCP Client**: `uvicorn client:app --host 0.0.0.0 --port 8001`
- **Web UI**: `python3 -m http.server 5173 --bind 0.0.0.0`

This allows external access when ports are mapped with Docker's `-p` flag.

### Docker Commands

### Build the image:
```bash
docker build -t mcp-server .
```

### Run with basic configuration:
```bash
docker run -d \
  --name mcp-container \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 5173:5173 \
  mcp-server
```

### Run with Ollama on host:
```bash
docker run -d \
  --name mcp-container \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 5173:5173 \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  mcp-server
```

### View logs:
```bash
docker logs -f mcp-container
```

### Stop and remove:
```bash
docker stop mcp-container
docker rm mcp-container
```

## Development

### Building for Development
```bash
# Build with development tags
docker build -t mcp-server:dev .

# Run with volume mounts for live editing
docker run -d \
  -p 8000:8000 -p 8001:8001 -p 5173:5173 \
  -v $(pwd)/server.py:/app/server.py \
  -v $(pwd)/client.py:/app/client.py \
  mcp-server:dev
```

### Docker Compose Development
```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f mcp-app

# Restart just the app
docker-compose restart mcp-app

# Rebuild and restart
docker-compose up --build -d
```

## Troubleshooting

### Common Issues

**"npm ci" fails with package lock out of sync**:
- This happens when `package.json` and `package-lock.json` are mismatched
- **Solution**: Regenerate the lock file before building:
  ```bash
  cd ui
  rm -f package-lock.json
  npm install
  cd ..
  docker build -t mcp-server-home .
  ```
- The Dockerfile now uses `npm ci` which requires exact version matches

**"Unsupported engine" warnings for Vite/React**:
- Modern Vite 7+ requires Node 20.19+ or 22.12+
- The Dockerfile now uses `node:22-alpine` for the build stage
- If you see this error, ensure you're using the latest Dockerfile

**"Connection refused" to Ollama**:
- Ensure Ollama is running: `ollama serve`
- Check the correct host URL for your platform:
  - Docker Desktop (Mac/Windows): `http://host.docker.internal:11434`
  - Linux: `http://172.17.0.1:11434` or your Docker bridge IP

**UI not loading**:
- Check that port 5173 is accessible
- Verify the UI build completed successfully in Docker logs
- Try accessing the client directly at http://localhost:8001

**Health check failing**:
- Services may still be starting up (wait 1-2 minutes)
- Check logs: `docker logs container_name`
- Verify required dependencies are available

### Getting Help

1. Check service health:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   ```

2. View container logs:
   ```bash
   docker logs mcp-container
   ```

3. Check running processes inside container:
   ```bash
   docker exec mcp-container ps aux
   ```

4. Access container shell:
   ```bash
   docker exec -it mcp-container bash
   ```

## Production Deployment

For production use:

1. Use specific image tags instead of `latest`
2. Set up proper environment variable management
3. Configure reverse proxy (nginx/traefik) with SSL
4. Set up log aggregation
5. Configure backup for MySQL volumes
6. Use Docker secrets for sensitive data

Example production docker-compose.yml:
```yaml
version: '3.8'
services:
  mcp-app:
    image: mcp-server:v1.0.0
    restart: always
    environment:
      - OLLAMA_URL=http://ollama.internal:11434
    secrets:
      - ha_token
      - mysql_password
    # ... additional production config
```