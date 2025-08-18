# Backend Management Scripts

This directory contains enhanced scripts for managing the Long Article Writer backend server with improved resilience, error handling, and logging.

## 📜 Available Scripts

### 🚀 `start_backend.sh` - Enhanced Server Startup
The main startup script with comprehensive error handling and dependency management.

#### Features:
- ✅ **Automatic Virtual Environment Setup**: Creates venv if missing
- ✅ **Dependency Management**: Installs/updates packages automatically
- ✅ **Conflict Resolution**: Fixes common dependency conflicts (marshmallow/environs)
- ✅ **Port Management**: Automatically handles port conflicts
- ✅ **Health Checks**: Validates imports and configuration
- ✅ **Detailed Logging**: Color-coded output with log files
- ✅ **Background Mode**: Optional daemon mode

#### Usage:
```bash
# Start in foreground (default)
./start_backend.sh

# Start in background
./start_backend.sh --background
# or
./start_backend.sh -d
```

#### What it does:
1. 🔍 Verifies directory structure and Python installation
2. 🐍 Creates/activates virtual environment
3. 📦 Installs/updates dependencies from requirements.txt
4. 🔧 Resolves known dependency conflicts automatically
5. 🧪 Tests critical imports
6. 🚪 Checks and manages port availability
7. 🚀 Starts the server with proper error handling

### 🛑 `stop_backend.sh` - Server Shutdown
Gracefully stops the backend server with multiple fallback methods.

#### Features:
- ✅ **PID-based Stopping**: Uses PID file for clean shutdown
- ✅ **Port-based Cleanup**: Finds and stops processes by port
- ✅ **Process Cleanup**: Kills any remaining uvicorn processes
- ✅ **Graceful → Force**: SIGTERM first, then SIGKILL if needed

#### Usage:
```bash
./stop_backend.sh
```

### 📊 `status_backend.sh` - Server Status Monitor
Comprehensive status checker with health monitoring and diagnostics.

#### Features:
- ✅ **Process Status**: Checks PID, port usage, and uvicorn processes
- ✅ **Health Endpoint**: Tests actual API responsiveness
- ✅ **Log Analysis**: Shows log file status and recent entries
- ✅ **System Info**: Displays URLs, file locations, and environment status

#### Usage:
```bash
# Basic status check
./status_backend.sh

# Show recent log entries
./status_backend.sh --tail
./status_backend.sh -t

# Show recent errors
./status_backend.sh --errors
./status_backend.sh -e

# Show help
./status_backend.sh --help
./status_backend.sh -h
```

## 📁 Log Files

All logs are stored in the `../logs/` directory:

- **`backend.log`**: Main application log with all startup steps and server output
- **`backend_errors.log`**: Error-specific log for troubleshooting
- **`server.pid`**: Process ID file (when running in background)

## 🎨 Color-Coded Output

The scripts use color-coded logging for better readability:
- 🟢 **Green [INFO]**: Successful operations
- 🟡 **Yellow [WARN]**: Warnings and non-critical issues
- 🔴 **Red [ERROR]**: Errors requiring attention
- 🔵 **Blue [STEP]**: Current operation steps

## 🔧 Configuration

Default settings in `start_backend.sh`:
```bash
PORT=8001              # Server port
HOST="0.0.0.0"        # Server host (all interfaces)
VENV_DIR="./venv"     # Virtual environment location
LOG_DIR="../logs"     # Log directory
```

## 🚨 Error Handling

### Common Issues and Automatic Fixes:

1. **Dependency Conflicts**:
   - Automatically resolves marshmallow/environs version conflicts
   - Retries package installation with fixes

2. **Port Conflicts**:
   - Automatically stops existing processes on the target port
   - Uses graceful shutdown (SIGTERM) followed by force kill if needed

3. **Missing Virtual Environment**:
   - Creates new virtual environment automatically
   - Installs all dependencies from scratch

4. **Import Errors**:
   - Tests critical imports before starting server
   - Provides diagnostic information for troubleshooting

### Manual Troubleshooting:

If the scripts fail, check the logs:
```bash
# View recent logs
./status_backend.sh --tail

# View errors
./status_backend.sh --errors

# Or directly view log files
tail -f ../logs/backend.log
cat ../logs/backend_errors.log
```

## 📝 Examples

### Complete Startup Flow:
```bash
# Stop any existing server
./stop_backend.sh

# Start fresh server
./start_backend.sh

# Check status
./status_backend.sh
```

### Background Server Management:
```bash
# Start in background
./start_backend.sh --background

# Check if running
./status_backend.sh

# View recent activity
./status_backend.sh --tail

# Stop when done
./stop_backend.sh
```

### Development Workflow:
```bash
# Start in foreground for development (auto-reload enabled)
./start_backend.sh

# In another terminal, monitor status
watch -n 5 './status_backend.sh'

# View logs in real-time
tail -f ../logs/backend.log
```

## 🌐 Server Endpoints

Once running, the server provides:
- **Health Check**: http://localhost:8001/api/health/
- **API Documentation**: http://localhost:8001/docs
- **Interactive API**: http://localhost:8001/redoc

## 🔒 Security Notes

- Server binds to `0.0.0.0:8001` by default (all interfaces)
- For production, consider changing `HOST` to `127.0.0.1` for localhost-only access
- Log files may contain sensitive information - secure accordingly

## 🤝 Contributing

To extend these scripts:
1. Follow the existing logging pattern using the provided functions
2. Add error handling with appropriate exit codes
3. Update this README with new features
4. Test thoroughly on different systems

---

*These scripts provide a robust foundation for backend development and deployment. For issues or enhancements, please refer to the main project documentation.*