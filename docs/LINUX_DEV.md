# Linux Development Setup Guide

Complete setup guide for developing the Model Context Protocol (MCP) project on Linux (Ubuntu/Debian-based distributions).

## Table of Contents

- [System Requirements](#system-requirements)
- [Python Setup](#python-setup)
- [Node.js Setup](#nodejs-setup)
- [Redis Setup](#redis-setup)
- [Ollama Setup](#ollama-setup)
- [Project Setup](#project-setup)
- [Running the Services](#running-the-services)
- [Development Tools](#development-tools)
- [Troubleshooting](#troubleshooting)

## System Requirements

- Ubuntu 20.04 LTS or later (or Debian-based distribution)
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
- Internet connection for downloading dependencies

## Python Setup

### 1. Install Python 3.10+

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3.10 python3.10-venv python3-pip -y

# Verify installation
python3 --version
pip3 --version
```

### 2. Install Development Tools

```bash
# Install build essentials for Python packages
sudo apt install build-essential python3-dev -y

# Install additional dependencies
sudo apt install libssl-dev libffi-dev -y
```

## Node.js Setup

### 1. Install Node.js via NodeSource

```bash
# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Verify installation
node --version
npm --version
```

### 2. Configure npm (Optional)

```bash
# Set npm to use a global directory you own
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'

# Add to PATH in ~/.bashrc
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

## Redis Setup

### 1. Install Redis Server

```bash
# Install Redis
sudo apt install redis-server -y

# Start Redis service
sudo systemctl start redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### 2. Configure Redis (Optional)

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Key settings to consider:
# - bind 127.0.0.1  (localhost only, more secure)
# - requirepass your_password  (add password protection)
# - maxmemory 256mb  (set memory limit)

# Restart Redis after changes
sudo systemctl restart redis-server
```

## Ollama Setup

### 1. Install Ollama

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

### 2. Download Required Model

```bash
# Pull the Qwen2.5 model (default for this project)
ollama pull qwen2.5:7b-instruct

# Verify the model is available
ollama list
```

### 3. Test Ollama

```bash
# Run a test query
ollama run qwen2.5:7b-instruct "Hello, how are you?"
```

### 4. Configure Ollama as a Service (Optional)

```bash
# Create systemd service file
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=$USER
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start ollama
sudo systemctl enable ollama
```

## Project Setup

### 1. Clone the Repository

```bash
# Clone the project
git clone <repository-url>
cd model-context-protocol
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy environment templates
cp .env.example .env
cp .env.client.example .env.client

# Edit configurations as needed
nano .env
nano .env.client
```

### 4. Install UI Dependencies

```bash
cd ui
npm install
cd ..
```

## Running the Services

### Option 1: Start Everything with One Command

```bash
# Make start script executable
chmod +x start.sh

# Start all services (server, client, UI)
./start.sh
```

This will start:
- MCP Server on `http://localhost:8000`
- MCP Client on `http://localhost:8001`
- Web UI on `http://localhost:5173`

### Option 2: Start Services Individually

```bash
# Terminal 1: Start MCP Server
source .venv/bin/activate
uvicorn server:app --reload --port 8000

# Terminal 2: Start MCP Client
source .venv/bin/activate
uvicorn client:app --reload --port 8001

# Terminal 3: Start Web UI
cd ui
npm run dev
```

### Run Tests

```bash
# Make test script executable
chmod +x test.sh

# Run comprehensive tests
./test.sh
```

## Development Tools

### Recommended IDE Setup

**Visual Studio Code:**
```bash
# Install VS Code
sudo snap install code --classic

# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
```

**PyCharm (Alternative):**
```bash
# Install PyCharm Community Edition
sudo snap install pycharm-community --classic
```

### Code Quality Tools

```bash
# Activate virtual environment first
source .venv/bin/activate

# Install development tools
pip install black flake8 mypy pytest

# Format code
black server.py client.py

# Lint code
flake8 server.py client.py

# Type checking
mypy server.py client.py
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using a port
sudo lsof -i :8000  # or :8001, :5173

# Kill the process
kill -9 <PID>
```

### Redis Connection Issues

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Restart Redis
sudo systemctl restart redis-server
```

### Ollama Issues

```bash
# Check Ollama status
systemctl --user status ollama

# View Ollama logs
journalctl --user -u ollama -f

# Restart Ollama
systemctl --user restart ollama
```

### Python Virtual Environment

```bash
# If venv activation doesn't work
deactivate  # if currently in a venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Permission Issues

```bash
# Fix script permissions
chmod +x start.sh test.sh

# Fix directory permissions
sudo chown -R $USER:$USER .
```

### Network/Firewall Issues

```bash
# Check if firewall is blocking ports
sudo ufw status

# Allow ports if needed
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 5173/tcp
```

## System Optimization

### Increase File Watchers (for development)

```bash
# Increase inotify watchers for hot-reload
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Improve Performance

```bash
# Install preload for faster application loading
sudo apt install preload -y

# Install zram for better memory management
sudo apt install zram-config -y
```

## Next Steps

1. Review the [README.md](./README.md) for usage instructions
2. Check [MCP_EXPLAINED.md](./MCP_EXPLAINED.md) for architecture details
3. See [CLIENT_ARCHITECTURE.md](./CLIENT_ARCHITECTURE.md) for client internals
4. Read [.github/copilot-instructions.md](./.github/copilot-instructions.md) if using AI assistants

## Additional Resources

- [Ubuntu Documentation](https://help.ubuntu.com/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Node.js on Linux](https://nodejs.org/en/download/package-manager/)
- [Redis Documentation](https://redis.io/docs/)
- [Ollama Documentation](https://github.com/ollama/ollama)
