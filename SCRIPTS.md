# Server Management Scripts

This directory contains convenient scripts to manage the Long Article Writer application servers.

## Quick Start

```bash
# Start all servers
./start-servers.sh

# Check server status
./status.sh

# Stop all servers
./stop-servers.sh
```

## Scripts Overview

### 🚀 `start-servers.sh`
- **Purpose**: Starts both backend and frontend servers in the background
- **Features**:
  - Automatically cleans up any existing processes
  - Waits for each service to be ready before proceeding
  - Creates PID files for process management
  - Logs output to `logs/` directory
  - Shows colored status updates

**Usage:**
```bash
./start-servers.sh
```

### 🛑 `stop-servers.sh`
- **Purpose**: Gracefully stops all running servers
- **Features**:
  - Attempts graceful shutdown first (SIGTERM)
  - Force kills if necessary (SIGKILL)
  - Cleans up PID files
  - Shows colored status updates

**Usage:**
```bash
./stop-servers.sh
```

### 📊 `status.sh`
- **Purpose**: Shows current status of all servers
- **Features**:
  - Tests actual HTTP connectivity
  - Shows process information
  - Lists helpful URLs and commands
  - Real-time status checking

**Usage:**
```bash
./status.sh
```

## Server Details

### Backend Server
- **Port**: 8000
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Log File**: `logs/backend.log`

### Frontend Server
- **Port**: 3005  
- **URL**: http://localhost:3005
- **Log File**: `logs/frontend.log`

## Log Management

View real-time logs:
```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log

# Both logs simultaneously
tail -f logs/*.log
```

## Troubleshooting

### Servers won't start
1. Check if ports are already in use:
   ```bash
   lsof -i :8000  # Backend
   lsof -i :3005  # Frontend
   ```

2. Check the log files:
   ```bash
   cat logs/backend.log
   cat logs/frontend.log
   ```

3. Ensure dependencies are installed:
   ```bash
   # Backend
   cd backend && pip install -r requirements.txt
   
   # Frontend  
   cd frontend && npm install
   ```

### Services appear running but not responding
1. Check the status script: `./status.sh`
2. Test endpoints manually:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:3005
   ```

### Clean restart
```bash
./stop-servers.sh
sleep 5
./start-servers.sh
```

## Environment Variables

The scripts automatically set these environment variables for the backend:

- `DATABASE_URL`: `mysql://root:~Brook1226,@127.0.0.1:3306/long_article_writer`
- `OLLAMA_HOST`: `localhost`
- `OLLAMA_PORT`: `11434`

## Background Process Management

- All servers run as background processes using `nohup`
- PID files are stored in `logs/` directory
- Output is redirected to log files
- Processes survive terminal closure

This approach ensures:
✅ Non-blocking server startup
✅ Clean process management  
✅ Easy monitoring and debugging
✅ Professional deployment practices