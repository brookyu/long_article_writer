#!/bin/bash

# Long Article Writer - Status Check Script
# This script checks the status of all servers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Long Article Writer Server Status${NC}"
echo "=================================="

# Function to check service status
check_service() {
    local url=$1
    local name=$2
    local port=$3
    
    echo -n "🔍 $name (port $port): "
    
    if curl -s --connect-timeout 3 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Running${NC}"
        return 0
    else
        echo -e "${RED}❌ Not responding${NC}"
        return 1
    fi
}

# Check Backend
check_service "http://localhost:8000/health" "Backend API" "8000"

# Check Frontend  
check_service "http://localhost:3005" "Frontend UI" "3005"

echo ""
echo -e "${BLUE}🔧 Process Information:${NC}"

# Show running processes
BACKEND_PROCS=$(ps aux | grep -E "python3.*app.main" | grep -v grep | wc -l | tr -d ' ')
FRONTEND_PROCS=$(ps aux | grep -E "node.*vite" | grep -v grep | wc -l | tr -d ' ')

echo "📊 Backend processes: $BACKEND_PROCS"
echo "🎨 Frontend processes: $FRONTEND_PROCS"

if [ "$BACKEND_PROCS" -gt 0 ] || [ "$FRONTEND_PROCS" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}📋 Running Processes:${NC}"
    ps aux | grep -E "(python3.*app.main|node.*vite)" | grep -v grep | while read line; do
        echo "  $line"
    done
fi

echo ""
echo -e "${BLUE}🌐 Application URLs:${NC}"
echo "  • Frontend: http://localhost:3005"
echo "  • Backend API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"

echo ""
echo -e "${BLUE}📝 Quick Commands:${NC}"
echo "  • Start servers:  ./start-servers.sh"
echo "  • Stop servers:   ./stop-servers.sh"
echo "  • View logs:      tail -f logs/backend.log"
echo "  •                 tail -f logs/frontend.log"