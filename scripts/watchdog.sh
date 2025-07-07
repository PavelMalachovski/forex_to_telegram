
#!/bin/bash

# Forex Bot Watchdog Script
# Monitors and restarts the application if it stops unexpectedly

LOG_FILE="/home/ubuntu/forex_bot_postgresql/logs/watchdog.log"
APP_DIR="/home/ubuntu/forex_bot_postgresql"
PYTHON_CMD="python enhanced_main.py"
MAX_RESTARTS=10
RESTART_COUNT=0
RESTART_DELAY=5

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] $1" | tee -a "$LOG_FILE"
}

check_process() {
    pgrep -f "enhanced_main.py" > /dev/null
    return $?
}

start_application() {
    log_message "Starting application..."
    cd "$APP_DIR"
    nohup $PYTHON_CMD > logs/app_watchdog.log 2>&1 &
    APP_PID=$!
    log_message "Application started with PID: $APP_PID"
    return 0
}

stop_application() {
    log_message "Stopping application gracefully..."
    pkill -TERM -f "enhanced_main.py"
    sleep 10
    
    if check_process; then
        log_message "Force killing application..."
        pkill -KILL -f "enhanced_main.py"
    fi
}

restart_application() {
    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        log_message "Maximum restart attempts ($MAX_RESTARTS) reached. Stopping watchdog."
        exit 1
    fi
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    log_message "Restart attempt $RESTART_COUNT/$MAX_RESTARTS"
    
    stop_application
    sleep $RESTART_DELAY
    start_application
    
    # Reset counter on successful restart
    if check_process; then
        sleep 30  # Wait 30 seconds to ensure stability
        if check_process; then
            RESTART_COUNT=0
            log_message "Application successfully restarted and stable"
        fi
    fi
}

# Signal handlers
trap 'log_message "Watchdog received SIGTERM, shutting down..."; stop_application; exit 0' TERM
trap 'log_message "Watchdog received SIGINT, shutting down..."; stop_application; exit 0' INT

log_message "Forex Bot Watchdog started"

# Initial start
if ! check_process; then
    start_application
fi

# Main monitoring loop
while true; do
    if ! check_process; then
        log_message "Application process not found, attempting restart..."
        restart_application
    fi
    
    sleep 30  # Check every 30 seconds
done
