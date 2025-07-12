
#!/bin/bash

# Start Forex Bot with comprehensive monitoring
# This script starts the application along with monitoring services

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
PID_DIR="$PROJECT_DIR/pids"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$PID_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_DIR/startup.log"
}

# Function to start service in background
start_service() {
    local service_name="$1"
    local script_path="$2"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    log_message "Starting $service_name..."
    
    # Kill existing process if running
    if [ -f "$pid_file" ]; then
        local old_pid
        old_pid=$(cat "$pid_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            log_message "Stopping existing $service_name (PID: $old_pid)"
            kill "$old_pid"
            sleep 2
        fi
        rm -f "$pid_file"
    fi
    
    # Start new process
    nohup bash "$script_path" > "$LOG_DIR/${service_name}.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"
    
    log_message "$service_name started with PID: $pid"
}

# Function to stop all services
stop_services() {
    log_message "Stopping all services..."
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid service_name
            pid=$(cat "$pid_file")
            service_name=$(basename "$pid_file" .pid)
            
            if kill -0 "$pid" 2>/dev/null; then
                log_message "Stopping $service_name (PID: $pid)"
                kill "$pid"
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Also stop the main application
    pkill -f "python.*production_scheduler.py" 2>/dev/null
    
    log_message "All services stopped"
}

# Function to check service status
check_services() {
    log_message "Checking service status..."
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid service_name
            pid=$(cat "$pid_file")
            service_name=$(basename "$pid_file" .pid)
            
            if kill -0 "$pid" 2>/dev/null; then
                log_message "$service_name: RUNNING (PID: $pid)"
            else
                log_message "$service_name: NOT RUNNING"
                rm -f "$pid_file"
            fi
        fi
    done
    
    # Check main application
    if pgrep -f "python.*production_scheduler.py" > /dev/null; then
        log_message "Main application: RUNNING"
    else
        log_message "Main application: NOT RUNNING"
    fi
}

# Function to start main application
start_main_app() {
    log_message "Starting main Forex Bot application..."
    cd "$PROJECT_DIR"
    
    # Set environment variables
    export LOG_DIR="$LOG_DIR"
    export PYTHONPATH="$PROJECT_DIR"
    
    # Start the application
    nohup python production_scheduler.py > "$LOG_DIR/app_main.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_DIR/main_app.pid"
    
    log_message "Main application started with PID: $pid"
    
    # Wait a bit and verify it's running
    sleep 10
    if kill -0 "$pid" 2>/dev/null; then
        log_message "Main application startup verified"
    else
        log_message "ERROR: Main application failed to start"
        return 1
    fi
}

# Main function
main() {
    case "${1:-start}" in
        start)
            log_message "=== Starting Forex Bot with monitoring ==="
            
            # Start main application first
            start_main_app
            
            # Start monitoring services
            start_service "watchdog" "$SCRIPT_DIR/watchdog.sh"
            start_service "monitor" "$SCRIPT_DIR/monitor.sh"
            
            log_message "=== All services started ==="
            check_services
            ;;
            
        stop)
            log_message "=== Stopping all services ==="
            stop_services
            ;;
            
        restart)
            log_message "=== Restarting all services ==="
            stop_services
            sleep 5
            main start
            ;;
            
        status)
            check_services
            ;;
            
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# Handle signals
trap 'stop_services; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
