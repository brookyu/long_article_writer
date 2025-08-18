#!/bin/bash

# Backend server status checker
# Author: AI Assistant

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$SCRIPT_DIR/server.pid"
LOG_FILE="$PROJECT_ROOT/logs/backend.log"
ERROR_LOG="$PROJECT_ROOT/logs/backend_errors.log"
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

log_status() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Backend Server Status                 ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if server is running
log_status "Checking server status..."

# Check PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log_info "✓ Server is running (PID: $PID)"
        SERVER_RUNNING=true
    else
        log_warn "PID file exists but process is not running"
        rm -f "$PID_FILE"
        SERVER_RUNNING=false
    fi
else
    SERVER_RUNNING=false
fi

# Check port
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    PORT_PID=$(lsof -ti:$PORT)
    log_info "✓ Port $PORT is in use by PID: $PORT_PID"
    PORT_IN_USE=true
else
    log_warn "✗ Port $PORT is not in use"
    PORT_IN_USE=false
fi

# Check uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn.*app.main:app" || true)
if [ ! -z "$UVICORN_PIDS" ]; then
    log_info "✓ Found uvicorn processes: $UVICORN_PIDS"
    UVICORN_RUNNING=true
else
    log_warn "✗ No uvicorn processes found"
    UVICORN_RUNNING=false
fi

echo ""

# Overall status
if [ "$SERVER_RUNNING" = true ] && [ "$PORT_IN_USE" = true ] && [ "$UVICORN_RUNNING" = true ]; then
    log_info "🟢 Backend server is RUNNING and healthy"
    
    # Test health endpoint
    echo ""
    log_status "Testing health endpoint..."
    if curl -s -f "http://localhost:$PORT/api/health/" > /dev/null 2>&1; then
        HEALTH_RESPONSE=$(curl -s "http://localhost:$PORT/api/health/")
        log_info "✓ Health check passed"
        echo "Response: $HEALTH_RESPONSE"
    else
        log_warn "✗ Health check failed"
    fi
    
elif [ "$PORT_IN_USE" = true ] || [ "$UVICORN_RUNNING" = true ]; then
    log_warn "🟡 Backend server appears to be partially running"
    log_warn "This might indicate an inconsistent state"
else
    log_error "🔴 Backend server is NOT running"
fi

echo ""

# System information
log_status "System Information:"
echo "• Server URL: http://localhost:$PORT"
echo "• Health check: http://localhost:$PORT/api/health/"
echo "• API docs: http://localhost:$PORT/docs"
echo "• Log file: $LOG_FILE"
echo "• Error log: $ERROR_LOG"

# Virtual environment status
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    log_info "✓ Virtual environment exists"
else
    log_warn "✗ Virtual environment not found"
fi

# Log file status
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
    log_info "✓ Log file exists ($LOG_SIZE lines)"
    
    if [ "$1" = "--tail" ] || [ "$1" = "-t" ]; then
        echo ""
        log_status "Recent log entries (last 10 lines):"
        echo "----------------------------------------"
        tail -10 "$LOG_FILE" 2>/dev/null || echo "Unable to read log file"
    fi
else
    log_warn "✗ Log file not found"
fi

# Error log status
if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
    ERROR_COUNT=$(wc -l < "$ERROR_LOG" 2>/dev/null || echo "0")
    log_warn "⚠ Error log has $ERROR_COUNT entries"
    
    if [ "$1" = "--errors" ] || [ "$1" = "-e" ]; then
        echo ""
        log_status "Recent errors (last 5 lines):"
        echo "----------------------------------------"
        tail -5 "$ERROR_LOG" 2>/dev/null || echo "Unable to read error log"
    fi
fi

echo ""

# Usage information
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --tail, -t     Show last 10 log entries"
    echo "  --errors, -e   Show last 5 error entries"
    echo "  --help, -h     Show this help message"
    echo ""
fi