
#!/bin/bash

# Watchdog script for Forex Bot
# This script monitors the application and restarts it if it fails

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
LOG_FILE="$LOG_DIR/watchdog.log"
HEALTH_CHECK_SCRIPT="$SCRIPT_DIR/health_check.sh"
CHECK_INTERVAL=60  # seconds
MAX_RESTART_ATTEMPTS=3
RESTART_DELAY=30   # seconds

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to start the application
start_application() {
    log_message "Starting Forex Bot application..."
    cd "$PROJECT_DIR"
    
    # Kill any existing processes
    pkill -f "python.*production_scheduler.py" 2>/dev/null
    sleep 5
    
    # Start the application in background
    nohup python production_scheduler.py > "$LOG_DIR/app_output.log" 2>&1 &
    local pid=$!
    
    log_message "Application started with PID: $pid"
    sleep 10  # Give it time to start
    
    # Verify it's running
    if pgrep -f "python.*production_scheduler.py" > /dev/null; then
        log_message "Application startup verified"
        return 0
    else
        log_message "Application failed to start"
        return 1
    fi
}

# Function to stop the application
stop_application() {
    log_message "Stopping Forex Bot application..."
    pkill -TERM -f "python.*production_scheduler.py" 2>/dev/null
    sleep 10
    
    # Force kill if still running
    if pgrep -f "python.*production_scheduler.py" > /dev/null; then
        log_message "Force killing application..."
        pkill -KILL -f "python.*production_scheduler.py" 2>/dev/null
    fi
    
    log_message "Application stopped"
}

# Function to restart the application
restart_application() {
    log_message "Restarting application..."
    stop_application
    sleep $RESTART_DELAY
    start_application
}

# Main watchdog loop
main() {
    log_message "Watchdog started for Forex Bot"
    local restart_count=0
    
    while true; do
        # Run health check
        if "$HEALTH_CHECK_SCRIPT" > /dev/null 2>&1; then
            log_message "Health check passed"
            restart_count=0  # Reset restart count on success
        else
            log_message "Health check failed"
            
            if [ $restart_count -lt $MAX_RESTART_ATTEMPTS ]; then
                restart_count=$((restart_count + 1))
                log_message "Attempting restart ($restart_count/$MAX_RESTART_ATTEMPTS)"
                
                if restart_application; then
                    log_message "Restart successful"
                else
                    log_message "Restart failed"
                fi
            else
                log_message "Maximum restart attempts reached. Manual intervention required."
                # Send alert (could be email, webhook, etc.)
                # For now, just log and continue monitoring
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Handle signals
trap 'log_message "Watchdog stopping..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
