#!/bin/bash

# Long Article Writer - Server Stop Script
# This script stops all running servers

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Long Article Writer servers...${NC}"

# Function to kill processes on a port
kill_port() {
    local port=$1
    local name=$2
    echo -e "${YELLOW}Stopping $name (port $port)...${NC}"
    
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 3
        # Force kill if still running
        local remaining_pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
        fi
        echo -e "${GREEN}✅ $name stopped${NC}"
    else
        echo -e "${YELLOW}⚪ $name was not running${NC}"
    fi
}

# Stop by port
kill_port 8000 "Backend Server"
kill_port 3005 "Frontend Server"

# Also kill by process name patterns
echo -e "${YELLOW}Cleaning up any remaining processes...${NC}"
pkill -f "python3.*app.main" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

# Clean up PID files
rm -f "$PROJECT_ROOT/logs/backend.pid" 2>/dev/null || true
rm -f "$PROJECT_ROOT/logs/frontend.pid" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All servers stopped successfully!${NC}"
echo ""
echo -e "${BLUE}📝 To restart servers:${NC}"
echo -e "  ./start-servers.sh"