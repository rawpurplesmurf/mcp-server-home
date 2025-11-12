# macOS Development Guide

## Overview

This guide provides macOS-specific information for developing and deploying the MCP (Model Context Protocol) ecosystem. The project was developed and optimized for macOS environments.

## System Requirements

### **macOS Version**
- **Minimum**: macOS 12.0 (Monterey)
- **Recommended**: macOS 13.0+ (Ventura) or macOS 14.0+ (Sonoma)
- **Tested On**: macOS 15.0+ (Sequoia)

### **Hardware Requirements**
- **CPU**: Apple Silicon (M1/M2/M3) or Intel x64
- **RAM**: 8GB minimum, 16GB+ recommended for Ollama models
- **Storage**: 10GB+ free space for models and dependencies
- **Network**: Stable internet connection for NTP and external tool testing

## macOS-Specific Setup

### 🍎 **Apple Silicon Optimizations**

#### **Python Environment**
```bash
# Use homebrew Python for best compatibility
brew install python@3.11

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
```

#### **Ollama Installation**
```bash
# Install via Homebrew (recommended for Apple Silicon)
brew install ollama

# Or download from ollama.ai for GUI installation
# Optimized for Apple Silicon performance
```

### 🔧 **Network Configuration**

#### **NTP Server Selection**
The project includes optimized NTP server configuration for macOS:

```bash
# .env configuration optimized for macOS
NTP_SERVER=time.apple.com        # Apple's NTP servers
NTP_BACKUP_SERVER=pool.ntp.org   # Global pool backup
NTP_TIMEOUT=5
```

#### **Network Interface Handling**
macOS handles network interfaces differently than Linux:

```python
# Ping command optimization for macOS
if os.name == 'nt':
    command = f"ping -n {self.PING_COUNT} {hostname}"
else:
    # macOS and Linux use similar ping syntax
    command = f"ping -c {self.PING_COUNT} {hostname}"
```

### 🚀 **Performance Optimizations**

#### **Apple Silicon Model Performance**
```bash
# Recommended models for Apple Silicon
ollama pull qwen2.5:7b-instruct    # Best balance of speed/capability
ollama pull llama3.1:8b-instruct   # Alternative high-performance option
ollama pull mistral:7b             # Lighter weight option
```

#### **Memory Management**
```bash
# Configure Ollama for optimal memory usage on macOS
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_KEEP_ALIVE=5m        # Manage model memory lifecycle
export OLLAMA_NUM_PARALLEL=1       # Adjust based on available RAM
```

## Development Workflow

### 🛠️ **Development Environment Setup**

#### **Terminal Configuration**
```bash
# Recommended terminal setup for development
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PATH="/opt/homebrew/bin:$PATH"  # For Apple Silicon homebrew

# Enable development mode
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
```

#### **VS Code Configuration**
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

### 🧪 **Testing on macOS**

#### **Running Both Servers**
```bash
# Terminal 1: Start MCP Server
source .venv/bin/activate
uvicorn server:app --port 8000 --reload

# Terminal 2: Start MCP Client  
source .venv/bin/activate
uvicorn client:app --port 8001 --reload

# Terminal 3: Test the system
curl http://localhost:8001/health
```

#### **Network Testing**
```bash
# Test network connectivity (macOS-specific hosts)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you ping apple.com?", "session_id": "macos-test"}'

# Test time synchronization with Apple's NTP
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?", "session_id": "macos-test"}'
```

## Troubleshooting

### 🔍 **Common macOS Issues**

#### **Port Already in Use**
```bash
# Find and kill processes using ports 8000/8001
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9

# Or use different ports
uvicorn server:app --port 8002
uvicorn client:app --port 8003
```

#### **Ollama Connection Issues**
```bash
# Check Ollama status
ollama list
ollama ps

# Restart Ollama service
brew services restart ollama

# Check Ollama logs
tail -f ~/.ollama/logs/server.log
```

#### **Python Virtual Environment Issues**
```bash
# Recreate virtual environment if corrupted
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r client_requirements.txt
```

#### **Network Permission Issues**
```bash
# Some network operations may require permissions
# Grant terminal/app network access in System Preferences → Security & Privacy
```

### 🐛 **Debugging Tools**

#### **Network Debugging**
```bash
# Test direct network connectivity
ping -c 4 pool.ntp.org
nc -zv localhost 11434  # Test Ollama connection

# Test NTP directly
sntp -sS pool.ntp.org
```

#### **Process Monitoring**
```bash
# Monitor server processes
ps aux | grep uvicorn
ps aux | grep ollama

# Monitor network connections
netstat -an | grep :800  # Check ports 8000/8001
```

## Performance Tuning

### ⚡ **Apple Silicon Optimizations**

#### **Model Loading Performance**
```bash
# Pre-load models to reduce first-request latency
ollama run qwen2.5:7b-instruct "Hello" # Warm up model

# Configure model persistence
export OLLAMA_KEEP_ALIVE=30m  # Keep models loaded longer
```

#### **Concurrent Request Handling**
```python
# Optimize for Apple Silicon's unified memory architecture
UVICORN_WORKERS = 1  # Single worker with async handling
UVICORN_WORKER_CONNECTIONS = 1000  # High connection limit
```

### 💾 **Storage Optimizations**

#### **Model Storage Location**
```bash
# Default Ollama model location on macOS
~/.ollama/models/

# Move to external storage if needed
export OLLAMA_MODELS=/Volumes/External/ollama-models
```

#### **Cache Configuration**
```bash
# Optimize Redis for macOS (if using)
# Use Unix socket for better performance
REDIS_HOST=unix:///tmp/redis.sock
```

## Deployment Considerations

### 🚀 **Production Deployment on macOS**

#### **System Service Setup**
Create `~/Library/LaunchAgents/mcp.server.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>mcp.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/project/.venv/bin/uvicorn</string>
        <string>server:app</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/project</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

#### **Load Services**
```bash
# Load the services
launchctl load ~/Library/LaunchAgents/mcp.server.plist
launchctl load ~/Library/LaunchAgents/mcp.client.plist

# Check service status
launchctl list | grep mcp
```

### 🔒 **Security Configuration**

#### **Firewall Settings**
```bash
# Allow incoming connections for development
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# Or configure specific port access
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/python
```

#### **Network Access Permissions**
- Grant network access in System Preferences → Security & Privacy → Privacy → Network
- Allow Python/Terminal network access when prompted

## Monitoring & Logging

### 📊 **macOS-Specific Monitoring**

#### **Console.app Integration**
```python
# Configure logging for macOS Console.app visibility
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'{os.path.expanduser("~/Library/Logs")}/mcp-server.log')
    ]
)
```

#### **Activity Monitor Integration**
- Monitor CPU/Memory usage through Activity Monitor
- Search for "uvicorn" and "ollama" processes
- Set up alerts for high resource usage

### 📈 **Performance Metrics**

#### **Native macOS Tools**
```bash
# CPU and memory monitoring
top -pid $(pgrep -f uvicorn)
vm_stat 1  # Memory statistics

# Network monitoring
nettop -p uvicorn  # Network activity by process
```

## Development Tips

### 💡 **macOS-Specific Best Practices**

1. **Use Homebrew Python**: More reliable than system Python
2. **Apple Silicon Optimization**: Leverage native ARM64 performance
3. **Terminal Management**: Use Terminal.app tabs for multi-server development
4. **File Watching**: macOS file system events work well with `--reload`
5. **Network Interfaces**: Be aware of WiFi/Ethernet interface switching

### 🔧 **Debugging Shortcuts**

```bash
# Quick health check script for macOS
#!/bin/bash
echo "=== MCP System Health Check ==="
echo "Server Status:"
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\nClient Status:"
curl -s http://localhost:8001/health | python3 -m json.tool

echo -e "\nOllama Status:"
ollama ps

echo -e "\nSystem Resources:"
echo "CPU: $(sysctl -n hw.ncpu) cores"
echo "Memory: $(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')"
```

## Conclusion

This macOS development guide provides the foundation for efficient development and deployment of the MCP ecosystem on Apple platforms. The project takes advantage of macOS's robust networking stack, Apple Silicon performance, and native development tools to provide an optimal experience for both development and production use.

For additional platform-specific questions or optimizations, refer to the main README.md and the comprehensive documentation provided in the project.