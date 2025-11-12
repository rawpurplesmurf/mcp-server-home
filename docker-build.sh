#!/bin/bash

# Docker Build and Run Script for MCP Server
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          MCP Server Docker Build & Deploy             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t mcp-server:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Choose deployment option:${NC}"
echo -e "  1) Simple container (app only, connects to external services)"
echo -e "  2) Full stack with Redis & MySQL"
echo -e "  3) Just build, don't run"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo -e "${YELLOW}Starting simple container...${NC}"
        echo -e "${BLUE}Make sure Ollama is running: ollama serve${NC}"
        
        # Check if container is already running
        if docker ps | grep -q mcp-container; then
            echo -e "${YELLOW}Stopping existing container...${NC}"
            docker stop mcp-container
            docker rm mcp-container
        fi
        
        docker run -d \
            --name mcp-container \
            -p 8000:8000 \
            -p 8001:8001 \
            -p 5173:5173 \
            -e OLLAMA_URL=http://host.docker.internal:11434 \
            mcp-server:latest
        
        echo -e "${GREEN}✓ Container started successfully${NC}"
        echo ""
        echo -e "${BLUE}Access your services:${NC}"
        echo -e "  🌐 Web UI:      ${YELLOW}http://localhost:5173${NC}"
        echo -e "  🤖 MCP Client:  ${YELLOW}http://localhost:8001${NC}"
        echo -e "  🖥️  MCP Server:  ${YELLOW}http://localhost:8000${NC}"
        echo ""
        echo -e "${YELLOW}View logs: ${NC}docker logs -f mcp-container"
        echo -e "${YELLOW}Stop container: ${NC}docker stop mcp-container"
        ;;
    2)
        echo -e "${YELLOW}Starting full stack with docker-compose...${NC}"
        
        # Check for required environment variables
        if [ -z "$MYSQL_PASSWORD" ]; then
            echo -e "${YELLOW}Setting default MySQL password...${NC}"
            export MYSQL_PASSWORD="mcp_password_$(date +%s)"
            echo -e "${BLUE}MySQL password: ${MYSQL_PASSWORD}${NC}"
        fi
        
        docker-compose up -d --build
        
        echo -e "${GREEN}✓ Full stack started successfully${NC}"
        echo ""
        echo -e "${BLUE}Services started:${NC}"
        echo -e "  🌐 Web UI:      ${YELLOW}http://localhost:5173${NC}"
        echo -e "  🤖 MCP Client:  ${YELLOW}http://localhost:8001${NC}"
        echo -e "  🖥️  MCP Server:  ${YELLOW}http://localhost:8000${NC}"
        echo -e "  📦 Redis:       ${YELLOW}localhost:6379${NC}"
        echo -e "  🗄️  MySQL:       ${YELLOW}localhost:3306${NC}"
        echo ""
        echo -e "${YELLOW}View logs: ${NC}docker-compose logs -f"
        echo -e "${YELLOW}Stop services: ${NC}docker-compose down"
        ;;
    3)
        echo -e "${GREEN}✓ Build complete. Image tagged as: mcp-server:latest${NC}"
        echo ""
        echo -e "${BLUE}To run manually:${NC}"
        echo -e "  docker run -p 8000:8000 -p 8001:8001 -p 5173:5173 mcp-server:latest"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}For more options, see DOCKER.md${NC}"