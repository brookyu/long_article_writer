#!/bin/bash

# Comprehensive start script for both backend and frontend servers
# Author: AI Assistant
# Description: Starts both backend and frontend servers with full health checking

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
STARTUP_LOG="$LOG_DIR/startup.log"

# Server configuration
BACKEND_PORT=8001
FRONTEND_PORT=3005
BACKEND_URL="http://localhost:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

# Create logs directory
mkdir -p "$LOG_DIR"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_backend() {
    echo -e "${PURPLE}[BACKEND]${NC} $1" | tee -a "$STARTUP_LOG"
}

log_frontend() {
    echo -e "${YELLOW}[FRONTEND]${NC} $1" | tee -a "$STARTUP_LOG"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Startup failed with exit code $exit_code"
        log_error "Check logs in: $LOG_DIR"
        log_error "Backend log: $BACKEND_LOG"
        log_error "Frontend log: $FRONTEND_LOG"
    fi
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT

# Enhanced port freeing function  
free_port() {
    local port=$1
    local name=$2
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0  # Port is free
        fi
        
        log_warn "$name port $port is in use, attempting to free it (attempt $attempt/$max_attempts)..."
        
        # Get all PIDs using the port
        EXISTING_PIDS=($(lsof -ti:$port 2>/dev/null || true))
        
        if [ ${#EXISTING_PIDS[@]} -eq 0 ]; then
            log_warn "No specific PIDs found, trying broader kill"
            # Try killing by process name
            pkill -f "uvicorn.*:$port" 2>/dev/null || true
            pkill -f "vite.*--port.*$port" 2>/dev/null || true
            pkill -f "node.*$port" 2>/dev/null || true
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
        
        # Additional cleanup
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
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
        log_error "Unable to free $name port $port after $max_attempts attempts"
        return 1
    fi
    
    log_info "✓ $name port $port successfully freed"
    return 0
}

# Wait for server function
wait_for_server() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    log_step "Waiting for $name to be ready at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_info "✓ $name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "✗ $name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Header
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Long Article Writer - Full Stack Startup    ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -d "$BACKEND_DIR" ] || [ ! -d "$FRONTEND_DIR" ]; then
    log_error "Backend or frontend directory not found!"
    log_error "Make sure you're running this script from the project root"
    exit 1
fi

# Parse arguments
BACKGROUND_MODE=false
if [ "$1" = "--background" ] || [ "$1" = "-d" ]; then
    BACKGROUND_MODE=true
    log_info "Starting in background mode..."
fi

# Check and free ports
log_step "Checking for existing servers..."

if ! free_port $BACKEND_PORT "Backend"; then
    log_error "Failed to free backend port"
    exit 1
fi

if ! free_port $FRONTEND_PORT "Frontend"; then
    log_error "Failed to free frontend port"  
    exit 1
fi

# Start Backend
log_step "Starting Backend Server..."
log_backend "Initializing backend at $BACKEND_URL"

if [ ! -x "$BACKEND_DIR/start_backend.sh" ]; then
    log_error "Backend startup script not found or not executable"
    log_error "Expected: $BACKEND_DIR/start_backend.sh"
    exit 1
fi

cd "$BACKEND_DIR"
if [ "$BACKGROUND_MODE" = true ]; then
    log_backend "Starting backend in background mode..."
    ./start_backend.sh --background > "$BACKEND_LOG" 2>&1 &
    BACKEND_STARTUP_PID=$!
    
    # Wait a moment for the backend script to complete
    sleep 5
    
    # Check if backend script completed successfully
    if ! kill -0 "$BACKEND_STARTUP_PID" 2>/dev/null; then
        wait "$BACKEND_STARTUP_PID"
        backend_exit_code=$?
        if [ $backend_exit_code -ne 0 ]; then
            log_error "Backend startup script failed"
            log_error "Check backend log: $BACKEND_LOG"
            exit 1
        fi
    fi
else
    log_backend "Starting backend in foreground mode..."
    ./start_backend.sh --background
fi

# Wait for backend to be ready
wait_for_server "$BACKEND_URL/api/health/" "Backend"
log_backend "✓ Backend server is running on $BACKEND_URL"

# Start Frontend
log_step "Starting Frontend Server..."
log_frontend "Initializing frontend at $FRONTEND_URL"

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    log_frontend "Installing frontend dependencies..."
    npm install > "$FRONTEND_LOG" 2>&1
fi

# Fix missing textarea component issue
log_frontend "Checking UI components..."
if [ ! -f "src/components/ui/textarea.tsx" ]; then
    log_frontend "Creating missing textarea component..."
    mkdir -p "src/components/ui"
    cat > "src/components/ui/textarea.tsx" << 'EOF'
import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
EOF
    log_frontend "✓ Textarea component created"
fi

# Start frontend server
if [ "$BACKGROUND_MODE" = true ]; then
    log_frontend "Starting frontend in background mode..."
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_DIR/server.pid"
    log_frontend "Frontend PID: $FRONTEND_PID"
else
    log_frontend "Starting frontend in background for testing..."
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_DIR/server.pid"
fi

# Wait for frontend to be ready
wait_for_server "$FRONTEND_URL" "Frontend"
log_frontend "✓ Frontend server is running on $FRONTEND_URL"

# Final status check
echo ""
log_step "Running final health checks..."

# Test backend health
if curl -s -f "$BACKEND_URL/api/health/" > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s "$BACKEND_URL/api/health/" | head -c 100)
    log_backend "✓ Backend health check passed"
    log_backend "Response: $HEALTH_RESPONSE..."
else
    log_error "✗ Backend health check failed"
    exit 1
fi

# Test frontend accessibility
if curl -s -f "$FRONTEND_URL" > /dev/null 2>&1; then
    log_frontend "✓ Frontend accessibility check passed"
else
    log_error "✗ Frontend accessibility check failed"
    exit 1
fi

# Success summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  🎉 ALL SERVERS STARTED SUCCESSFULLY!        ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${PURPLE}🔗 Application URLs:${NC}"
echo -e "   Frontend:  ${YELLOW}$FRONTEND_URL${NC}"
echo -e "   Backend:   ${YELLOW}$BACKEND_URL${NC}"
echo -e "   API Docs:  ${YELLOW}$BACKEND_URL/docs${NC}"
echo -e "   Health:    ${YELLOW}$BACKEND_URL/api/health/${NC}"
echo ""
echo -e "${BLUE}📋 Process Information:${NC}"
if [ -f "$BACKEND_DIR/server.pid" ]; then
    BACKEND_PID=$(cat "$BACKEND_DIR/server.pid")
    echo -e "   Backend PID:  ${GREEN}$BACKEND_PID${NC}"
fi
if [ -f "$FRONTEND_DIR/server.pid" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_DIR/server.pid")
    echo -e "   Frontend PID: ${GREEN}$FRONTEND_PID${NC}"
fi
echo ""
echo -e "${BLUE}📁 Log Files:${NC}"
echo -e "   Startup:  ${YELLOW}$STARTUP_LOG${NC}"
echo -e "   Backend:  ${YELLOW}$BACKEND_LOG${NC}"
echo -e "   Frontend: ${YELLOW}$FRONTEND_LOG${NC}"
echo ""
echo -e "${BLUE}🛑 To Stop Servers:${NC}"
echo -e "   ${YELLOW}./stop_servers.sh${NC}"
echo ""
echo -e "${BLUE}📊 To Check Status:${NC}"
echo -e "   ${YELLOW}./status_servers.sh${NC}"
echo ""

if [ "$BACKGROUND_MODE" = false ]; then
    log_info "Servers are running! Open $FRONTEND_URL in your browser to test."
    log_info "Press Ctrl+C to stop all servers"
    
    # Keep script running to maintain servers
    while true; do
        sleep 5
        # Check if servers are still running
        if ! lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_error "Backend server stopped unexpectedly"
            break
        fi
        if ! lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_error "Frontend server stopped unexpectedly"
            break
        fi
    done
fi