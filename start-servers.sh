#!/bin/bash

# Long Article Writer - Server Startup Script
# This script starts all required servers in the background

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Starting Long Article Writer servers from: $PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill processes on a port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Cleaning up port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $name to start...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $name failed to start after $max_attempts seconds${NC}"
    return 1
}

echo "🧹 Cleaning up any existing processes..."

# Kill existing processes
kill_port 8000  # Backend
kill_port 3005  # Frontend

echo -e "${BLUE}📊 Starting Backend Server...${NC}"

# Start Backend
cd "$PROJECT_ROOT/backend"
DATABASE_URL="mysql://root:~Brook1226,@127.0.0.1:3306/long_article_writer" \
OLLAMA_HOST="localhost" \
OLLAMA_PORT="11434" \
nohup python3 -m app.main > ../logs/backend.log 2>&1 &

BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to be ready
if wait_for_service "http://localhost:8000/health" "Backend"; then
    echo -e "${GREEN}✅ Backend server running at http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check logs/backend.log${NC}"
    exit 1
fi

echo -e "${BLUE}🎨 Starting Frontend Server...${NC}"

# Start Frontend
cd "$PROJECT_ROOT/frontend"
nohup npm run dev > ../logs/frontend.log 2>&1 &

FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to be ready
if wait_for_service "http://localhost:3005" "Frontend"; then
    echo -e "${GREEN}✅ Frontend server running at http://localhost:3005${NC}"
else
    echo -e "${RED}❌ Frontend failed to start. Check logs/frontend.log${NC}"
    exit 1
fi

# Create PID file for easy management
echo "$BACKEND_PID" > "$PROJECT_ROOT/logs/backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/logs/frontend.pid"

echo ""
echo -e "${GREEN}🎉 All servers started successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Server Status:${NC}"
echo -e "  🔧 Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo -e "  🎨 Frontend: http://localhost:3005 (PID: $FRONTEND_PID)"
echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo -e "  • View backend logs:  tail -f logs/backend.log"
echo -e "  • View frontend logs: tail -f logs/frontend.log"
echo -e "  • Stop all servers:   ./stop-servers.sh"
echo ""
echo -e "${YELLOW}💡 Open http://localhost:3005 in your browser to use the application!${NC}"