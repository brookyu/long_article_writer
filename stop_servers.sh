#!/bin/bash

# Comprehensive stop script for both backend and frontend servers
# Author: AI Assistant

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

BACKEND_PORT=8001
FRONTEND_PORT=3005

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_backend() {
    echo -e "${PURPLE}[BACKEND]${NC} $1"
}

log_frontend() {
    echo -e "${YELLOW}[FRONTEND]${NC} $1"
}

# Stop function with multiple methods
stop_service() {
    local service_name=$1
    local port=$2
    local pid_file=$3
    local process_pattern=$4
    
    echo ""
    echo -e "${BLUE}Stopping $service_name...${NC}"
    
    local stopped=false
    
    # Method 1: Stop using PID file
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $service_name with PID: $pid"
            kill -TERM "$pid" 2>/dev/null || true
            sleep 3
            
            # Check if still running
            if ! kill -0 "$pid" 2>/dev/null; then
                rm -f "$pid_file"
                log_info "✓ $service_name stopped successfully (PID method)"
                stopped=true
            else
                log_warn "Process still running, force killing..."
                kill -KILL "$pid" 2>/dev/null || true
                rm -f "$pid_file"
                stopped=true
            fi
        else
            log_warn "PID in file ($pid) is not running"
            rm -f "$pid_file"
        fi
    fi
    
    # Method 2: Stop by port
    if [ "$stopped" = false ] && lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_info "Found $service_name on port $port, stopping..."
        local pids=$(lsof -ti:$port)
        for pid in $pids; do
            log_info "Killing process $pid"
            kill -TERM "$pid" 2>/dev/null || true
        done
        sleep 3
        
        # Force kill if still running
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            pids=$(lsof -ti:$port)
            for pid in $pids; do
                log_warn "Force killing process $pid"
                kill -KILL "$pid" 2>/dev/null || true
            done
        fi
        stopped=true
    fi
    
    # Method 3: Stop by process pattern
    if [ "$stopped" = false ] && [ ! -z "$process_pattern" ]; then
        local pids=$(pgrep -f "$process_pattern" || true)
        if [ ! -z "$pids" ]; then
            log_info "Found $service_name processes: $pids"
            echo $pids | xargs kill -TERM 2>/dev/null || true
            sleep 3
            
            # Force kill if still running
            pids=$(pgrep -f "$process_pattern" || true)
            if [ ! -z "$pids" ]; then
                log_warn "Force killing remaining processes..."
                echo $pids | xargs kill -KILL 2>/dev/null || true
            fi
            stopped=true
        fi
    fi
    
    # Verify stopped
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "✗ Failed to stop $service_name on port $port"
        return 1
    else
        log_info "✓ $service_name stopped successfully"
        return 0
    fi
}

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Stopping Long Article Writer Servers        ${NC}"
echo -e "${BLUE}================================================${NC}"

# Stop Backend
stop_service "Backend" "$BACKEND_PORT" "$BACKEND_DIR/server.pid" "uvicorn.*app.main:app"
backend_result=$?

# Also try the backend's own stop script
if [ -x "$BACKEND_DIR/stop_backend.sh" ]; then
    log_backend "Running backend stop script..."
    cd "$BACKEND_DIR"
    ./stop_backend.sh
fi

# Stop Frontend  
stop_service "Frontend" "$FRONTEND_PORT" "$FRONTEND_DIR/server.pid" "vite.*dev"
frontend_result=$?

# Stop any remaining npm/node processes related to the project
log_frontend "Cleaning up remaining frontend processes..."
pkill -f "npm.*run.*dev" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

# Clean up any remaining processes
echo ""
echo -e "${BLUE}Final cleanup...${NC}"

# Kill any remaining processes on our ports
for port in $BACKEND_PORT $FRONTEND_PORT; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warn "Force cleaning port $port"
        lsof -ti:$port | xargs kill -KILL 2>/dev/null || true
    fi
done

# Remove PID files
rm -f "$BACKEND_DIR/server.pid" "$FRONTEND_DIR/server.pid"

# Summary
echo ""
if [ $backend_result -eq 0 ] && [ $frontend_result -eq 0 ]; then
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✅ ALL SERVERS STOPPED SUCCESSFULLY         ${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    log_info "Both backend and frontend servers have been stopped"
    log_info "All processes cleaned up and ports freed"
else
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}  ⚠️  SOME ISSUES OCCURRED DURING SHUTDOWN    ${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    if [ $backend_result -ne 0 ]; then
        log_error "Backend shutdown had issues"
    fi
    if [ $frontend_result -ne 0 ]; then
        log_error "Frontend shutdown had issues"
    fi
    log_warn "Manual intervention may be required"
fi

echo ""
echo -e "${BLUE}📋 Port Status:${NC}"
echo -e "   Backend ($BACKEND_PORT):  $(lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1 && echo "${RED}In Use${NC}" || echo "${GREEN}Free${NC}")"
echo -e "   Frontend ($FRONTEND_PORT): $(lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1 && echo "${RED}In Use${NC}" || echo "${GREEN}Free${NC}")"
echo ""