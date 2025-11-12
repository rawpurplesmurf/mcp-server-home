# Windows Development Setup Guide

Complete setup guide for developing the Model Context Protocol (MCP) project on Windows 10/11.

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

- Windows 10 (version 1903+) or Windows 11
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
- Internet connection for downloading dependencies
- Administrator access for installations

## Python Setup

### 1. Install Python 3.10+

**Option A: Official Installer (Recommended)**

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"

**Option B: Microsoft Store**

1. Open Microsoft Store
2. Search for "Python 3.10" or higher
3. Click "Get" to install

**Verify Installation:**

```powershell
python --version
pip --version
```

### 2. Install Build Tools (for some packages)

Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/):
- Select "Desktop development with C++"
- Install

## Node.js Setup

### 1. Install Node.js

1. Download from [nodejs.org](https://nodejs.org/) (LTS version recommended)
2. Run the installer
3. Accept defaults (includes npm)
4. Restart your terminal

**Verify Installation:**

```powershell
node --version
npm --version
```

### 2. Configure npm (Optional)

```powershell
# Set execution policy if needed
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Configure npm cache location (optional)
npm config set cache "C:\npm-cache" --global
```

## Redis Setup

### Option 1: Redis via WSL2 (Recommended)

**Install WSL2:**

```powershell
# Run as Administrator
wsl --install
# Restart computer
```

**Install Redis in WSL2:**

```bash
# In WSL2 terminal
sudo apt update
sudo apt install redis-server -y

# Start Redis
sudo service redis-server start

# Test connection
redis-cli ping
```

**Access from Windows:**
Redis will be available at `localhost:6379`

### Option 2: Memurai (Native Windows Redis)

1. Download [Memurai](https://www.memurai.com/get-memurai) (free for development)
2. Run installer
3. Memurai runs as a Windows service automatically

**Test Connection:**

```powershell
# Using redis-cli (if installed)
redis-cli ping

# Or use Memurai CLI
memurai-cli ping
```

### Option 3: Docker Desktop

```powershell
# Install Docker Desktop from docker.com
# Then run Redis in a container:
docker run -d -p 6379:6379 --name redis redis:alpine

# Test connection
docker exec -it redis redis-cli ping
```

## Ollama Setup

### 1. Install Ollama

1. Download Ollama from [ollama.com](https://ollama.com/download)
2. Run the installer
3. Ollama will start automatically as a service

**Verify Installation:**

```powershell
ollama --version
```

### 2. Download Required Model

```powershell
# Pull the Qwen2.5 model (default for this project)
ollama pull qwen2.5:7b-instruct

# Verify the model is available
ollama list
```

### 3. Test Ollama

```powershell
# Run a test query
ollama run qwen2.5:7b-instruct "Hello, how are you?"
```

**Ollama runs as a background service and starts with Windows.**

## Project Setup

### 1. Install Git (if needed)

Download and install [Git for Windows](https://git-scm.com/download/win)

### 2. Clone the Repository

```powershell
# Using PowerShell or Git Bash
git clone <repository-url>
cd model-context-protocol
```

### 3. Set Up Python Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.\.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```powershell
# Copy environment templates
copy .env.example .env
copy .env.client.example .env.client

# Edit configurations with notepad
notepad .env
notepad .env.client
```

### 5. Install UI Dependencies

```powershell
cd ui
npm install
cd ..
```

## Running the Services

### PowerShell Script (Recommended)

Create a `start.ps1` file:

```powershell
# start.ps1
Write-Host "Starting MCP Server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn server:app --reload --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting MCP Client..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn client:app --reload --port 8001"

Start-Sleep -Seconds 2

Write-Host "Starting Web UI..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\ui'; npm run dev"

Write-Host "`nAll services started!" -ForegroundColor Green
Write-Host "Web UI: http://localhost:5173" -ForegroundColor Yellow
Write-Host "MCP Client: http://localhost:8001" -ForegroundColor Yellow
Write-Host "MCP Server: http://localhost:8000" -ForegroundColor Yellow
```

**Run the script:**

```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
```

### Manual Start (Alternative)

**Terminal 1: MCP Server**
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn server:app --reload --port 8000
```

**Terminal 2: MCP Client**
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn client:app --reload --port 8001
```

**Terminal 3: Web UI**
```powershell
cd ui
npm run dev
```

### Run Tests

```powershell
# Activate venv first
.\.venv\Scripts\Activate.ps1

# Install test dependencies
pip install pytest httpx

# Run Python tests (if available)
python test_client.py
```

## Development Tools

### Recommended IDE Setup

**Visual Studio Code (Recommended):**

1. Download from [code.visualstudio.com](https://code.visualstudio.com/)
2. Install recommended extensions:
   - Python (Microsoft)
   - Pylance
   - ESLint
   - Prettier

**PyCharm (Alternative):**

Download from [jetbrains.com/pycharm](https://www.jetbrains.com/pycharm/)

### Windows Terminal (Recommended)

Install [Windows Terminal](https://www.microsoft.com/store/productId/9N0DX20HK701) from Microsoft Store for better terminal experience.

### Code Quality Tools

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

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

```powershell
# Find process using a port
netstat -ano | findstr :8000

# Kill process by PID
taskkill /PID <PID> /F
```

### Python Not Found

```powershell
# Check if Python is in PATH
$env:PATH

# Add Python to PATH manually (adjust path as needed)
$env:PATH += ";C:\Users\YourName\AppData\Local\Programs\Python\Python310"
```

### Redis Connection Issues

**For WSL2 Redis:**
```powershell
# Check WSL2 status
wsl --list --running

# Restart WSL2
wsl --shutdown
wsl
```

**For Memurai:**
```powershell
# Check service status
Get-Service Memurai

# Restart service
Restart-Service Memurai
```

### Ollama Issues

```powershell
# Check if Ollama is running
ollama list

# Restart Ollama service
Restart-Service Ollama
```

### Virtual Environment Activation Issues

```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Try activating again
.\.venv\Scripts\Activate.ps1

# Alternative: Use Command Prompt instead
.\.venv\Scripts\activate.bat
```

### Firewall Issues

If services can't communicate:

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Add Python and Node.js
4. Allow both Private and Public networks

### Long Path Issues

If you encounter "path too long" errors:

```powershell
# Enable long paths (requires Administrator)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

## Performance Tips

### Exclude from Windows Defender

Add project folder to exclusions for better performance:

1. Open Windows Security
2. Go to Virus & threat protection
3. Manage settings → Exclusions
4. Add folder: `C:\path\to\model-context-protocol`

### Use SSD Storage

Store the project on an SSD for faster file operations and hot-reload.

### WSL2 Performance

For better WSL2 performance, store projects in WSL2 filesystem (`\\wsl$\Ubuntu\home\...`) rather than Windows filesystem.

## Next Steps

1. Review the [README.md](./README.md) for usage instructions
2. Check [MCP_EXPLAINED.md](./MCP_EXPLAINED.md) for architecture details
3. See [CLIENT_ARCHITECTURE.md](./CLIENT_ARCHITECTURE.md) for client internals
4. Read [.github/copilot-instructions.md](./.github/copilot-instructions.md) if using AI assistants

## Additional Resources

- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Node.js on Windows](https://nodejs.org/en/download/)
- [WSL2 Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Windows Terminal](https://docs.microsoft.com/en-us/windows/terminal/)
