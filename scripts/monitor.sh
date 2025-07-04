
#!/bin/bash

# Continuous monitoring script for Forex Bot
# Runs health checks at regular intervals and maintains logs

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_CHECK_SCRIPT="$SCRIPT_DIR/health_check.sh"
CHECK_INTERVAL=60  # seconds
LOG_FILE="/home/ubuntu/forex_bot_postgresql/logs/monitor.log"
PID_FILE="/tmp/forex_bot_monitor.pid"
MAX_LOG_SIZE=10485760  # 10MB
BACKUP_LOGS=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [MONITOR] $1" | tee -a "$LOG_FILE"
}

# Rotate logs if they get too large
rotate_logs() {
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
        log "Rotating log file (size exceeded $MAX_LOG_SIZE bytes)"
        
        # Rotate existing backups
        for i in $(seq $((BACKUP_LOGS-1)) -1 1); do
            if [ -f "${LOG_FILE}.$i" ]; then
                mv "${LOG_FILE}.$i" "${LOG_FILE}.$((i+1))"
            fi
        done
        
        # Move current log to .1
        mv "$LOG_FILE" "${LOG_FILE}.1"
        
        # Remove oldest backup if it exists
        if [ -f "${LOG_FILE}.$((BACKUP_LOGS+1))" ]; then
            rm "${LOG_FILE}.$((BACKUP_LOGS+1))"
        fi
        
        log "Log rotation completed"
    fi
}

# Check if another instance is running
check_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Monitor is already running with PID $pid"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
}

# Signal handlers
cleanup() {
    log "Monitor stopping..."
    rm -f "$PID_FILE"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start monitoring
start_monitor() {
    check_running
    
    # Write PID file
    echo $$ > "$PID_FILE"
    
    log "Starting Forex Bot monitor (PID: $$, interval: ${CHECK_INTERVAL}s)"
    
    local consecutive_failures=0
    local last_status="unknown"
    
    while true; do
        rotate_logs
        
        # Run health check
        if "$HEALTH_CHECK_SCRIPT" --restart >/dev/null 2>&1; then
            if [ "$last_status" != "healthy" ]; then
                log "✓ Health check PASSED"
                if [ $consecutive_failures -gt 0 ]; then
                    log "Service recovered after $consecutive_failures consecutive failures"
                fi
            fi
            consecutive_failures=0
            last_status="healthy"
        else
            consecutive_failures=$((consecutive_failures + 1))
            log "✗ Health check FAILED (consecutive failures: $consecutive_failures)"
            last_status="unhealthy"
            
            # Alert on multiple consecutive failures
            if [ $consecutive_failures -eq 3 ]; then
                log "WARNING: 3 consecutive health check failures detected"
            elif [ $consecutive_failures -eq 5 ]; then
                log "CRITICAL: 5 consecutive health check failures detected"
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Stop monitoring
stop_monitor() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping monitor (PID: $pid)"
            kill "$pid"
            rm -f "$PID_FILE"
            echo "Monitor stopped"
        else
            echo "Monitor is not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "Monitor is not running"
    fi
}

# Show monitor status
status_monitor() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}Monitor is running${NC} (PID: $pid)"
            
            # Show recent log entries
            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "Recent log entries:"
                tail -n 10 "$LOG_FILE"
            fi
        else
            echo -e "${RED}Monitor PID file exists but process is not running${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}Monitor is not running${NC}"
    fi
}

# Show logs
show_logs() {
    local lines="${1:-50}"
    
    if [ -f "$LOG_FILE" ]; then
        echo "Last $lines lines from monitor log:"
        echo "=================================="
        tail -n "$lines" "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 {start|stop|restart|status|logs} [options]"
    echo ""
    echo "Commands:"
    echo "  start     Start the monitor daemon"
    echo "  stop      Stop the monitor daemon"
    echo "  restart   Restart the monitor daemon"
    echo "  status    Show monitor status"
    echo "  logs      Show recent log entries"
    echo ""
    echo "Options for 'logs':"
    echo "  -n NUM    Show NUM lines (default: 50)"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start monitoring"
    echo "  $0 status             # Check if monitoring is running"
    echo "  $0 logs -n 100        # Show last 100 log lines"
}

# Main script logic
case "${1:-}" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    restart)
        stop_monitor
        sleep 2
        start_monitor
        ;;
    status)
        status_monitor
        ;;
    logs)
        if [ "${2:-}" = "-n" ] && [ -n "${3:-}" ]; then
            show_logs "$3"
        else
            show_logs
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac
