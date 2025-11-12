# MCP Web UI

A modern, responsive chat interface for interacting with the Model Context Protocol (MCP) system.

## Features

- 🎨 **Modern Dark Theme**: Sleek, professional dark UI design
- 💬 **Real-time Chat**: Instant interaction with the MCP client
- 🔧 **Tool Visibility**: Visual badges showing which MCP tools were used (NTP time, ping)
- 📱 **Fully Responsive**: Works on desktop, tablet, and mobile
- ⚡ **Fast Loading**: Built with Vite for instant hot-reload
- 🗨️ **Clear Chat**: Button to clear conversation history
- 🎯 **Auto-scroll**: Always shows the latest messages

## Quick Start

### Option 1: Start All Services (Recommended)

From the project root:
```bash
npm start
# Or: bash scripts/start.sh
```

### Option 2: Start UI Only

If MCP Server and Client are already running:
```bash
cd ui
npm install
npm run dev
```

## Installation

### Install all dependencies (including Playwright for testing):
```bash
cd ui
npm install
npx playwright install chromium
```

### Or install from project root:
```bash
npm run install:all
# Or just UI:
npm run install:ui
```

## Example Queries

- "What time is it?" - Uses NTP time tool
- "Can you ping google.com?" - Uses ping tool
- "Hello, what can you do?" - General conversation
