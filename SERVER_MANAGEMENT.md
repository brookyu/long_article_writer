# Long Article Writer - Server Management System

## 🚀 Overview

This project now includes a comprehensive, production-ready server management system that handles both backend (FastAPI) and frontend (React + Vite) servers with advanced error handling, health monitoring, and automated recovery.

## 📜 Available Scripts

### 🌟 **`start_servers.sh`** - Full Stack Startup
The main script that starts both backend and frontend servers with comprehensive health checking.

#### Features:
- ✅ **Automatic Environment Setup**: Creates virtual environments, installs dependencies
- ✅ **Port Conflict Resolution**: Automatically handles port conflicts
- ✅ **Health Monitoring**: Waits for servers to be ready before proceeding
- ✅ **Component Fixing**: Automatically creates missing UI components
- ✅ **Background/Foreground Modes**: Flexible deployment options
- ✅ **Comprehensive Logging**: Detailed startup logs with timestamps

#### Usage:
```bash
# Start both servers (will run until Ctrl+C)
./start_servers.sh

# Start both servers in background mode
./start_servers.sh --background
./start_servers.sh -d
```

### 🛑 **`stop_servers.sh`** - Complete Shutdown
Gracefully stops both backend and frontend servers with multiple fallback methods.

#### Features:
- ✅ **Multi-Method Stopping**: PID file → Port-based → Process pattern
- ✅ **Graceful Shutdown**: SIGTERM first, then SIGKILL if needed
- ✅ **Complete Cleanup**: Removes PID files, frees ports
- ✅ **Comprehensive Verification**: Ensures all processes are stopped

#### Usage:
```bash
./stop_servers.sh
```

### 📊 **`status_servers.sh`** - System Monitoring
Advanced status checker with health monitoring and diagnostics for both servers.

#### Features:
- ✅ **Full Stack Status**: Backend + Frontend health checking
- ✅ **Real Health Testing**: HTTP calls to actual endpoints
- ✅ **Environment Validation**: Checks virtual environments, dependencies
- ✅ **Log Analysis**: Shows log file status and recent entries
- ✅ **Port Monitoring**: Real-time port usage information

#### Usage:
```bash
# Basic status check
./status_servers.sh

# Show recent log entries
./status_servers.sh --tail
./status_servers.sh -t

# Show recent errors
./status_servers.sh --errors
./status_servers.sh -e

# Show help
./status_servers.sh --help
./status_servers.sh -h
```

## 🌐 **Currently Running Services**

### ✅ **Backend Server**
- **URL**: http://localhost:8001
- **Health**: http://localhost:8001/api/health/
- **API Docs**: http://localhost:8001/docs
- **Status**: 🟢 **RUNNING** (PID: 60514)

### ✅ **Frontend Server**  
- **URL**: http://localhost:3005
- **Status**: 🟢 **RUNNING** (PID: 60546)

## 🎯 **Quick Start Guide**

### **Test the Application Right Now:**
1. **Frontend**: Open http://localhost:3005 in your browser
2. **Backend API**: Visit http://localhost:8001/docs for interactive API documentation
3. **Health Check**: http://localhost:8001/api/health/

### **Full Development Workflow:**
```bash
# Check current status
./status_servers.sh

# Stop all servers
./stop_servers.sh

# Start fresh (development mode)
./start_servers.sh

# Or start in background for testing
./start_servers.sh --background

# Monitor status
./status_servers.sh --tail
```

## 📁 **Log Management**

All logs are centralized in the `logs/` directory:

### **Log Files:**
- **`startup.log`**: Full stack startup process
- **`backend.log`**: Backend server output and requests
- **`frontend.log`**: Frontend server output and build logs
- **`backend_errors.log`**: Backend-specific errors

### **Viewing Logs:**
```bash
# Recent logs from all services
./status_servers.sh --tail

# Error analysis
./status_servers.sh --errors

# Live backend logs
tail -f logs/backend.log

# Live frontend logs  
tail -f logs/frontend.log
```

## 🔧 **Advanced Features**

### **Automatic Problem Resolution:**
- **Missing Virtual Environment**: Creates and configures automatically
- **Dependency Conflicts**: Resolves marshmallow/environs version issues
- **Missing Components**: Creates missing UI components (like textarea)
- **Port Conflicts**: Gracefully stops conflicting processes
- **Network Issues**: Waits for services to be ready before proceeding

### **Health Monitoring:**
- **Backend Health**: Tests `/api/health/` endpoint
- **Frontend Accessibility**: Verifies Vite server response
- **Process Validation**: Monitors PID files and process status
- **Port Monitoring**: Real-time port usage tracking

### **Error Recovery:**
- **Graceful Failures**: Clear error messages with suggested fixes
- **Automatic Retry**: Attempts multiple methods for process management
- **Resource Cleanup**: Ensures no orphaned processes or locked ports

## 🎨 **Color-Coded Output**

The scripts use intuitive color coding:
- 🟢 **Green [INFO]**: Successful operations
- 🟡 **Yellow [WARN]**: Warnings and non-critical issues
- 🔴 **Red [ERROR]**: Errors requiring attention
- 🔵 **Blue [STEP]**: Current operation steps
- 🟣 **Purple [BACKEND]**: Backend-specific messages
- 🟡 **Yellow [FRONTEND]**: Frontend-specific messages

## 🛡️ **Production Considerations**

### **Security:**
- Backend binds to `0.0.0.0:8001` (all interfaces) for development
- For production, consider changing to `127.0.0.1` for localhost-only
- Log files may contain sensitive information - secure accordingly

### **Performance:**
- Scripts include timeout mechanisms (60 seconds for server startup)
- Background mode available for daemon deployment
- Process monitoring prevents resource leaks

### **Monitoring:**
- Health endpoints provide real-time status
- Log files include timestamps and request tracking
- Status script provides comprehensive system overview

## 🔄 **Integration Examples**

### **CI/CD Pipeline:**
```bash
# In your CI script
./start_servers.sh --background
./status_servers.sh
# Run tests
./stop_servers.sh
```

### **Development Setup:**
```bash
# One-time setup
git clone <repository>
cd long_article_writer
./start_servers.sh --background

# Daily development
./status_servers.sh
# Code changes are auto-reloaded
# When done:
./stop_servers.sh
```

### **Testing Workflow:**
```bash
# Start servers for testing
./start_servers.sh --background

# Verify all services
./status_servers.sh

# Run your tests against:
# - Frontend: http://localhost:3005
# - Backend: http://localhost:8001

# Check logs if issues
./status_servers.sh --tail

# Clean shutdown
./stop_servers.sh
```

## 🆘 **Troubleshooting**

### **Common Issues:**

1. **Port Already in Use:**
   - Scripts automatically detect and resolve port conflicts
   - Manual fix: `./stop_servers.sh` then `./start_servers.sh`

2. **Missing Dependencies:**
   - Backend: Script automatically installs from requirements.txt
   - Frontend: Script runs `npm install` if node_modules missing

3. **Service Not Starting:**
   - Check logs: `./status_servers.sh --errors`
   - View detailed logs: `tail -f logs/startup.log`

4. **Health Check Failing:**
   - Backend: Check `logs/backend.log`
   - Frontend: Check `logs/frontend.log`
   - Network: Verify no firewall blocking ports

### **Manual Recovery:**
```bash
# Force stop everything
pkill -f uvicorn
pkill -f "npm.*run.*dev"
pkill -f "node.*vite"

# Clean start
./start_servers.sh
```

## 📊 **Monitoring Dashboard**

For continuous monitoring, run:
```bash
# Real-time status updates every 5 seconds
watch -n 5 './status_servers.sh'

# Or create an alias for quick checks
alias check='./status_servers.sh'
alias start='./start_servers.sh --background'
alias stop='./stop_servers.sh'
```

---

**🎉 Your Long Article Writer application is now running with enterprise-grade server management!**

Visit **http://localhost:3005** to start using the application with its new chat-based AI article generation features.

For support or issues, check the logs first with `./status_servers.sh --tail` or `./status_servers.sh --errors`.