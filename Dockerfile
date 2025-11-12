# Multi-stage Dockerfile for MCP Server + Client + UI
FROM node:18-alpine AS ui-builder

# Build the React UI
WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci --only=production

COPY ui/ ./
RUN npm run build

# Python runtime stage
FROM python:3.11-slim AS python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    iputils-ping \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application files
COPY server.py client.py ./
COPY .env.example .env.client.example ./

# Copy built UI from previous stage
COPY --from=ui-builder /app/ui/dist ./ui/dist

# Copy startup scripts and create Docker startup script
COPY scripts/start.sh scripts/
COPY start-docker.sh ./
RUN chmod +x scripts/start.sh start-docker.sh

# Expose ports
EXPOSE 8000 8001 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health && \
        curl -f http://localhost:8001/health || exit 1

# Default command
CMD ["./start-docker.sh"]