#!/bin/bash

# Enhanced backend startup script with resilience and error handling
# Author: AI Assistant
# Description: Robust startup script for the long article writer backend

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/backend.log"
ERROR_LOG="$LOG_DIR/backend_errors.log"
PORT=8001
HOST="0.0.0.0"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ERROR_LOG"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Script failed with exit code $exit_code"
        log_error "Check logs at: $ERROR_LOG"
    fi
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT

# Header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Long Article Writer Backend Startup  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the correct directory
log_step "Verifying directory structure..."
cd "$SCRIPT_DIR"

if [ ! -f "app/main.py" ]; then
    log_error "app/main.py not found! Are you in the correct directory?"
    log_error "Current directory: $(pwd)"
    exit 1
fi
log_info "✓ Backend directory structure verified"

# Check Python version
log_step "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 is not installed or not in PATH"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
log_info "✓ Found $PYTHON_VERSION"

# Check if virtual environment exists
log_step "Checking virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    log_warn "Virtual environment not found. Creating one..."
    python3 -m venv "$VENV_DIR"
    log_info "✓ Virtual environment created at $VENV_DIR"
else
    log_info "✓ Virtual environment found at $VENV_DIR"
fi

# Activate virtual environment
log_step "Activating virtual environment..."
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    log_error "Virtual environment activation script not found"
    exit 1
fi

source "$VENV_DIR/bin/activate"
log_info "✓ Virtual environment activated"

# Verify Python in venv
VENV_PYTHON=$(which python)
log_info "Using Python: $VENV_PYTHON"

# Check if requirements.txt exists
log_step "Checking requirements..."
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found!"
    exit 1
fi

# Install/update dependencies
log_step "Installing/updating dependencies..."
log_info "Installing packages from requirements.txt..."

# Upgrade pip first
python -m pip install --upgrade pip 2>&1 | tee -a "$LOG_FILE"

# Install requirements with error handling
if ! python -m pip install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"; then
    log_error "Failed to install some packages. Attempting to fix common issues..."
    
    # Try to fix common dependency conflicts
    log_warn "Attempting to resolve dependency conflicts..."
    
    # Fix known conflicts
    python -m pip install "marshmallow>=3.0.0,<4.0.0" 2>&1 | tee -a "$LOG_FILE"
    python -m pip install "environs==9.5.0" 2>&1 | tee -a "$LOG_FILE"
    
    # Retry requirements installation
    if ! python -m pip install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"; then
        log_error "Failed to install dependencies even after conflict resolution"
        log_error "Please check $LOG_FILE for details"
        exit 1
    fi
fi

log_info "✓ Dependencies installed successfully"

# Test imports
log_step "Testing critical imports..."
if ! python -c "import app.main; print('✓ Main app imports successfully')" 2>&1 | tee -a "$LOG_FILE"; then
    log_error "Failed to import main application"
    log_error "There may be missing dependencies or configuration issues"
    
    # Try to provide helpful information
    log_info "Attempting to diagnose the issue..."
    python -c "
import sys
print(f'Python version: {sys.version}')
print(f'Python path: {sys.executable}')
try:
    import app
    print('✓ App module found')
except ImportError as e:
    print(f'✗ App import error: {e}')
" 2>&1 | tee -a "$LOG_FILE"
    
    exit 1
fi

log_info "✓ Application imports successfully"

# Function to aggressively free port
free_port() {
    local port=$1
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_step "Checking if port $port is available (attempt $attempt/$max_attempts)..."
        
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_info "✓ Port $port is available"
            return 0
        fi
        
        log_warn "Port $port is in use, attempting to free it..."
        
        # Get all PIDs using the port
        EXISTING_PIDS=($(lsof -ti:$port 2>/dev/null || true))
        
        if [ ${#EXISTING_PIDS[@]} -eq 0 ]; then
            log_warn "No specific PIDs found, trying broader kill"
            # Try killing by process name
            pkill -f "uvicorn.*:$port" 2>/dev/null || true
            pkill -f "python.*uvicorn.*$port" 2>/dev/null || true
            sleep 2
        else
            log_warn "Found PIDs using port $port: ${EXISTING_PIDS[*]}"
            
            # First attempt: Graceful termination
            for pid in "${EXISTING_PIDS[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    log_warn "Sending TERM signal to PID $pid"
                    kill -TERM "$pid" 2>/dev/null || true
                fi
            done
            
            sleep 3
            
            # Second attempt: Force kill any remaining
            for pid in "${EXISTING_PIDS[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    log_warn "Force killing PID $pid"
                    kill -KILL "$pid" 2>/dev/null || true
                fi
            done
            
            sleep 2
        fi
        
        # Additional cleanup attempts
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warn "Port still in use, trying additional cleanup methods..."
            
            # Try killing all uvicorn processes
            pkill -9 -f uvicorn 2>/dev/null || true
            sleep 1
            
            # Try killing all Python processes on this port
            pids_to_kill=$(lsof -ti:$port 2>/dev/null || true)
            if [ ! -z "$pids_to_kill" ]; then
                echo "$pids_to_kill" | xargs -r kill -9 2>/dev/null || true
                sleep 1
            fi
        fi
        
        attempt=$((attempt + 1))
    done
    
    # Final check
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "Unable to free port $port after $max_attempts attempts"
        log_error "Please manually run: pkill -9 -f uvicorn && sleep 2"
        return 1
    fi
    
    log_info "✓ Port $port successfully freed"
    return 0
}

# Free the port before starting
if ! free_port $PORT; then
    exit 1
fi

# Set environment variables
log_step "Setting up environment..."
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
log_info "✓ Environment configured"

# Start the server
log_step "Starting backend server..."
log_info "Server will be available at: http://$HOST:$PORT"
log_info "Health check: http://localhost:$PORT/api/health/"
log_info "API documentation: http://localhost:$PORT/docs"
log_info ""
log_info "Press Ctrl+C to stop the server"
log_info "Logs are being written to: $LOG_FILE"
log_info ""

# Start server with proper error handling
if [ "$1" = "--background" ] || [ "$1" = "-d" ]; then
    log_info "Starting server in background mode..."
    nohup python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > "$SCRIPT_DIR/server.pid"
    log_info "✓ Server started in background (PID: $SERVER_PID)"
    log_info "To stop: kill $SERVER_PID or run: pkill -f uvicorn"
else
    log_info "Starting server in foreground mode..."
    exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload 2>&1 | tee -a "$LOG_FILE"
fi