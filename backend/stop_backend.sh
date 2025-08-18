#!/bin/bash

# Stop backend server script
# Author: AI Assistant

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/server.pid"
PORT=8001

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Stopping Backend Server              ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Try to stop using PID file first
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log_info "Stopping server with PID: $PID"
        kill -TERM "$PID"
        sleep 2
        
        # Check if still running
        if kill -0 "$PID" 2>/dev/null; then
            log_warn "Server still running, force killing..."
            kill -KILL "$PID"
        fi
        
        rm -f "$PID_FILE"
        log_info "✓ Server stopped successfully"
    else
        log_warn "PID in file ($PID) is not running"
        rm -f "$PID_FILE"
    fi
else
    log_warn "No PID file found, trying to find process by port..."
fi

# Kill any process on the port
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_info "Found process on port $PORT, stopping..."
    PIDS=$(lsof -ti:$PORT)
    for pid in $PIDS; do
        log_info "Killing process $pid"
        kill -TERM "$pid" 2>/dev/null || true
    done
    sleep 2
    
    # Force kill if still running
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PIDS=$(lsof -ti:$PORT)
        for pid in $PIDS; do
            log_warn "Force killing process $pid"
            kill -KILL "$pid" 2>/dev/null || true
        done
    fi
fi

# Kill any uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn.*app.main:app" || true)
if [ ! -z "$UVICORN_PIDS" ]; then
    log_info "Found uvicorn processes: $UVICORN_PIDS"
    echo $UVICORN_PIDS | xargs kill -TERM 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    UVICORN_PIDS=$(pgrep -f "uvicorn.*app.main:app" || true)
    if [ ! -z "$UVICORN_PIDS" ]; then
        log_warn "Force killing remaining uvicorn processes..."
        echo $UVICORN_PIDS | xargs kill -KILL 2>/dev/null || true
    fi
fi

# Verify everything is stopped
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_error "Failed to stop all processes on port $PORT"
    log_error "Manual intervention may be required"
    exit 1
else
    log_info "✓ All backend processes stopped successfully"
fi

echo ""