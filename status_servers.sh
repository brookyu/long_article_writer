#!/bin/bash

# Comprehensive status script for both backend and frontend servers
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
BACKEND_URL="http://localhost:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

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

log_backend() {
    echo -e "${PURPLE}[BACKEND]${NC} $1"
}

log_frontend() {
    echo -e "${YELLOW}[FRONTEND]${NC} $1"
}

# Check service status
check_service_status() {
    local service_name=$1
    local port=$2
    local pid_file=$3
    local health_url=$4
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $service_name Status${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local is_running=false
    local pid=""
    
    # Check PID file
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "✓ $service_name is running (PID: $pid)"
            is_running=true
        else
            log_warn "PID file exists but process is not running"
            rm -f "$pid_file"
        fi
    fi
    
    # Check port
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local port_pid=$(lsof -ti:$port)
        log_info "✓ Port $port is in use by PID: $port_pid"
        if [ "$is_running" = false ]; then
            pid=$port_pid
            is_running=true
        fi
    else
        log_warn "✗ Port $port is not in use"
    fi
    
    # Test health endpoint if provided
    if [ ! -z "$health_url" ] && [ "$is_running" = true ]; then
        echo ""
        log_status "Testing $service_name endpoint..."
        if curl -s -f "$health_url" > /dev/null 2>&1; then
            if [[ "$health_url" == *"/api/health/"* ]]; then
                local health_response=$(curl -s "$health_url")
                log_info "✓ Health check passed"
                echo "    Response: $health_response"
            else
                log_info "✓ Endpoint accessible"
            fi
        else
            log_warn "✗ Endpoint not accessible"
        fi
    fi
    
    # Overall status
    echo ""
    if [ "$is_running" = true ]; then
        log_info "🟢 $service_name is RUNNING and healthy"
    else
        log_error "🔴 $service_name is NOT running"
    fi
    
    return $( [ "$is_running" = true ] && echo 0 || echo 1 )
}

# Parse arguments
SHOW_LOGS=false
SHOW_ERRORS=false
SHOW_HELP=false

case "$1" in
    --tail|-t)
        SHOW_LOGS=true
        ;;
    --errors|-e)
        SHOW_ERRORS=true
        ;;
    --help|-h)
        SHOW_HELP=true
        ;;
esac

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Long Article Writer - Server Status          ${NC}"
echo -e "${BLUE}================================================${NC}"

# Check Backend Status
check_service_status "Backend" "$BACKEND_PORT" "$BACKEND_DIR/server.pid" "$BACKEND_URL/api/health/"
backend_status=$?

# Check Frontend Status  
check_service_status "Frontend" "$FRONTEND_PORT" "$FRONTEND_DIR/server.pid" "$FRONTEND_URL"
frontend_status=$?

# Overall System Status
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Overall System Status${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $backend_status -eq 0 ] && [ $frontend_status -eq 0 ]; then
    log_info "🟢 FULL STACK RUNNING - All systems operational"
elif [ $backend_status -eq 0 ] || [ $frontend_status -eq 0 ]; then
    log_warn "🟡 PARTIAL SYSTEM RUNNING - Some services down"
else
    log_error "🔴 ALL SYSTEMS DOWN - No services running"
fi

# System Information
echo ""
echo -e "${BLUE}📋 System Information:${NC}"
echo -e "   Project Root:     ${YELLOW}$SCRIPT_DIR${NC}"
echo -e "   Backend Dir:      ${YELLOW}$BACKEND_DIR${NC}"
echo -e "   Frontend Dir:     ${YELLOW}$FRONTEND_DIR${NC}"
echo ""
echo -e "${BLUE}🔗 Application URLs:${NC}"
echo -e "   Frontend:         ${YELLOW}$FRONTEND_URL${NC} $(curl -s -f "$FRONTEND_URL" > /dev/null 2>&1 && echo "${GREEN}[LIVE]${NC}" || echo "${RED}[DOWN]${NC}")"
echo -e "   Backend:          ${YELLOW}$BACKEND_URL${NC} $(curl -s -f "$BACKEND_URL/api/health/" > /dev/null 2>&1 && echo "${GREEN}[LIVE]${NC}" || echo "${RED}[DOWN]${NC}")"
echo -e "   API Docs:         ${YELLOW}$BACKEND_URL/docs${NC}"
echo -e "   Health Check:     ${YELLOW}$BACKEND_URL/api/health/${NC}"
echo ""
echo -e "${BLUE}📂 Log Files:${NC}"
echo -e "   Startup Log:      ${YELLOW}$LOG_DIR/startup.log${NC} $([ -f "$LOG_DIR/startup.log" ] && echo "${GREEN}[EXISTS]${NC}" || echo "${RED}[MISSING]${NC}")"
echo -e "   Backend Log:      ${YELLOW}$LOG_DIR/backend.log${NC} $([ -f "$LOG_DIR/backend.log" ] && echo "${GREEN}[EXISTS]${NC}" || echo "${RED}[MISSING]${NC}")"
echo -e "   Frontend Log:     ${YELLOW}$LOG_DIR/frontend.log${NC} $([ -f "$LOG_DIR/frontend.log" ] && echo "${GREEN}[EXISTS]${NC}" || echo "${RED}[MISSING]${NC}")"

# Environment Status
echo ""
echo -e "${BLUE}🔧 Environment Status:${NC}"

# Backend environment
if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
    log_info "✓ Backend virtual environment exists"
else
    log_warn "✗ Backend virtual environment not found"
fi

# Frontend environment
if [ -f "$FRONTEND_DIR/package.json" ]; then
    log_info "✓ Frontend package.json exists"
    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        log_info "✓ Frontend dependencies installed"
    else
        log_warn "✗ Frontend dependencies not installed"
    fi
else
    log_warn "✗ Frontend package.json not found"
fi

# Port information
echo ""
echo -e "${BLUE}🔌 Port Status:${NC}"
echo -e "   Backend ($BACKEND_PORT):       $(lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1 && echo "${GREEN}In Use${NC}" || echo "${YELLOW}Free${NC}")"
echo -e "   Frontend ($FRONTEND_PORT):      $(lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1 && echo "${GREEN}In Use${NC}" || echo "${YELLOW}Free${NC}")"

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo ""
    echo -e "${BLUE}📜 Recent Log Entries:${NC}"
    
    if [ -f "$LOG_DIR/startup.log" ]; then
        echo ""
        echo -e "${YELLOW}Startup Log (last 10 lines):${NC}"
        echo "----------------------------------------"
        tail -10 "$LOG_DIR/startup.log" 2>/dev/null || echo "Unable to read startup log"
    fi
    
    if [ -f "$LOG_DIR/backend.log" ]; then
        echo ""
        echo -e "${PURPLE}Backend Log (last 10 lines):${NC}"
        echo "----------------------------------------"
        tail -10 "$LOG_DIR/backend.log" 2>/dev/null || echo "Unable to read backend log"
    fi
    
    if [ -f "$LOG_DIR/frontend.log" ]; then
        echo ""
        echo -e "${YELLOW}Frontend Log (last 10 lines):${NC}"
        echo "----------------------------------------"
        tail -10 "$LOG_DIR/frontend.log" 2>/dev/null || echo "Unable to read frontend log"
    fi
fi

# Show errors if requested
if [ "$SHOW_ERRORS" = true ]; then
    echo ""
    echo -e "${BLUE}⚠️  Error Information:${NC}"
    
    if [ -f "$BACKEND_DIR/../logs/backend_errors.log" ] && [ -s "$BACKEND_DIR/../logs/backend_errors.log" ]; then
        echo ""
        echo -e "${RED}Backend Errors (last 5 lines):${NC}"
        echo "----------------------------------------"
        tail -5 "$BACKEND_DIR/../logs/backend_errors.log" 2>/dev/null || echo "Unable to read backend errors"
    else
        log_info "No backend errors logged"
    fi
    
    # Check for frontend errors in log
    if [ -f "$LOG_DIR/frontend.log" ]; then
        echo ""
        echo -e "${RED}Frontend Errors (from log):${NC}"
        echo "----------------------------------------"
        grep -i error "$LOG_DIR/frontend.log" | tail -5 || echo "No frontend errors found"
    fi
fi

# Control commands
echo ""
echo -e "${BLUE}🎛️  Control Commands:${NC}"
echo -e "   Start All:        ${YELLOW}./start_servers.sh${NC}"
echo -e "   Stop All:         ${YELLOW}./stop_servers.sh${NC}"
echo -e "   Status (current): ${YELLOW}./status_servers.sh${NC}"
echo -e "   Status + Logs:    ${YELLOW}./status_servers.sh --tail${NC}"
echo -e "   Status + Errors:  ${YELLOW}./status_servers.sh --errors${NC}"

# Help information
if [ "$SHOW_HELP" = true ]; then
    echo ""
    echo -e "${BLUE}📖 Usage Information:${NC}"
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --tail, -t     Show last 10 log entries for each service"
    echo "  --errors, -e   Show recent error entries"
    echo "  --help, -h     Show this help message"
    echo ""
fi

echo ""