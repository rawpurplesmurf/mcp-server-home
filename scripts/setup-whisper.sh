#!/bin/bash
# Quick setup script for Whisper voice transcription

set -e

echo "🎤 MCP Voice Input Setup"
echo "========================"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker found"
echo ""

# Check if .env.client exists
if [ ! -f ".env.client" ]; then
    echo "Creating .env.client from example..."
    cp .env.client.example .env.client
    echo "✓ .env.client created"
else
    echo "✓ .env.client exists"
fi

# Prompt for Whisper setup
echo ""
echo "Choose Whisper container setup:"
echo "1) Basic (CPU only, base model) - Fast, moderate accuracy"
echo "2) Medium model (CPU only) - Slower, better accuracy"
echo "3) GPU accelerated (requires NVIDIA GPU) - Fast, best accuracy"
echo "4) Skip - I'll set up Whisper myself"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "Starting Whisper container (basic setup)..."
        docker run -d -p 9000:9000 \
            --name whisper \
            --restart unless-stopped \
            onerahmet/openai-whisper-asr-webservice:latest
        
        if [ $? -eq 0 ]; then
            echo "✓ Whisper container started"
            WHISPER_URL="http://localhost:9000"
        else
            echo "❌ Failed to start Whisper container"
            exit 1
        fi
        ;;
    2)
        echo ""
        echo "Starting Whisper container (medium model)..."
        docker run -d -p 9000:9000 \
            --name whisper \
            --restart unless-stopped \
            -e ASR_MODEL=medium \
            onerahmet/openai-whisper-asr-webservice:latest
        
        if [ $? -eq 0 ]; then
            echo "✓ Whisper container started"
            WHISPER_URL="http://localhost:9000"
        else
            echo "❌ Failed to start Whisper container"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "Starting Whisper container (GPU accelerated)..."
        docker run -d -p 9000:9000 \
            --name whisper \
            --restart unless-stopped \
            --gpus all \
            -e ASR_MODEL=base \
            -e ASR_ENGINE=faster_whisper \
            onerahmet/openai-whisper-asr-webservice:latest
        
        if [ $? -eq 0 ]; then
            echo "✓ Whisper container started"
            WHISPER_URL="http://localhost:9000"
        else
            echo "❌ Failed to start Whisper container (check GPU support)"
            exit 1
        fi
        ;;
    4)
        echo ""
        read -p "Enter your Whisper URL (e.g., http://192.168.1.100:9000): " WHISPER_URL
        
        if [ -z "$WHISPER_URL" ]; then
            echo "❌ No URL provided"
            exit 1
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Update .env.client with Whisper URL
echo ""
echo "Configuring .env.client..."

if grep -q "^WHISPER_URL=" .env.client; then
    # Update existing line
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^WHISPER_URL=.*|WHISPER_URL=$WHISPER_URL|" .env.client
    else
        # Linux
        sed -i "s|^WHISPER_URL=.*|WHISPER_URL=$WHISPER_URL|" .env.client
    fi
    echo "✓ Updated WHISPER_URL in .env.client"
else
    # Add new line
    echo "WHISPER_URL=$WHISPER_URL" >> .env.client
    echo "✓ Added WHISPER_URL to .env.client"
fi

# Test Whisper connection if it's a local container
if [[ $choice -ne 4 ]]; then
    echo ""
    echo "Waiting for Whisper to start..."
    sleep 5
    
    for i in {1..12}; do
        if curl -s http://localhost:9000 > /dev/null 2>&1; then
            echo "✓ Whisper is responding"
            break
        fi
        
        if [ $i -eq 12 ]; then
            echo "⚠ Whisper may not be ready yet. Check with: docker logs whisper"
        else
            sleep 5
        fi
    done
fi

echo ""
echo "✅ Voice input setup complete!"
echo ""
echo "Next steps:"
echo "1. Start/restart the MCP client:"
echo "   npm run dev:client"
echo ""
echo "2. Open the web UI:"
echo "   http://localhost:5173"
echo ""
echo "3. Click the 🎤 microphone button to test voice input"
echo ""
echo "Useful commands:"
echo "- Check Whisper status: docker ps | grep whisper"
echo "- View Whisper logs: docker logs whisper"
echo "- Stop Whisper: docker stop whisper"
echo "- Remove Whisper: docker rm whisper"
echo ""
echo "📖 Full documentation: docs/VOICE_INPUT.md"
