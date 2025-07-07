
#!/bin/bash

# Enhanced startup script with monitoring and auto-restart capabilities
# This script provides temporary workaround for SIGTERM issues

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_RESTARTS=${MAX_RESTARTS:-5}
RESTART_DELAY=${RESTART_DELAY:-10}
LOG_DIR="/home/ubuntu/forex_bot_postgresql/logs"
MONITOR_INTERVAL=${MONITOR_INTERVAL:-30}

# Create log directory
mkdir -p "$LOG_DIR"

log_message() {
    local message="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    echo -e "[$timestamp] $message" | tee -a "$LOG_DIR/startup.log"
}

cleanup() {
    log_message "${YELLOW}🧹 Cleaning up processes...${NC}"
    
    # Kill background processes
    if [ -n "$MONITOR_PID" ]; then
        kill $MONITOR_PID 2>/dev/null || true
    fi
    
    if [ -n "$RESOURCE_CHECK_PID" ]; then
        kill $RESOURCE_CHECK_PID 2>/dev/null || true
    fi
    
    # Kill main application if running
    pkill -f "python.*enhanced_main.py" 2>/dev/null || true
    
    log_message "${GREEN}✅ Cleanup completed${NC}"
    exit 0
}

# Setup signal handlers
trap cleanup INT TERM

start_monitoring() {
    log_message "${BLUE}🔍 Starting resource monitoring...${NC}"
    
    # Start resource monitor
    python monitor_resources.py \
        --interval $MONITOR_INTERVAL \
        --log-file "$LOG_DIR/resource_monitor.log" &
    MONITOR_PID=$!
    
    # Start resource check script
    bash render_resource_check.sh &
    RESOURCE_CHECK_PID=$!
    
    log_message "${GREEN}✅ Monitoring started (PIDs: $MONITOR_PID, $RESOURCE_CHECK_PID)${NC}"
}

start_application() {
    log_message "${BLUE}🚀 Starting main application...${NC}"
    
    # Start the main application
    python enhanced_main.py &
    APP_PID=$!
    
    log_message "${GREEN}✅ Application started (PID: $APP_PID)${NC}"
    return $APP_PID
}

wait_for_health() {
    local max_wait=60
    local wait_time=0
    local port=${PORT:-10000}
    
    log_message "${BLUE}🏥 Waiting for application health check...${NC}"
    
    while [ $wait_time -lt $max_wait ]; do
        if curl -s --max-time 5 "http://localhost:$port/health" > /dev/null 2>&1; then
            log_message "${GREEN}✅ Application is healthy${NC}"
            return 0
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
        log_message "Waiting for health... (${wait_time}s/${max_wait}s)"
    done
    
    log_message "${RED}❌ Application failed to become healthy within ${max_wait}s${NC}"
    return 1
}

main() {
    log_message "${GREEN}🚀 Enhanced Startup Script for Render${NC}"
    log_message "Max restarts: $MAX_RESTARTS"
    log_message "Restart delay: ${RESTART_DELAY}s"
    log_message "Monitor interval: ${MONITOR_INTERVAL}s"
    
    # Check environment
    if [ -n "$RENDER_EXTERNAL_HOSTNAME" ]; then
        log_message "${GREEN}✅ Running on Render: $RENDER_EXTERNAL_HOSTNAME${NC}"
    else
        log_message "${YELLOW}⚠️ Running locally${NC}"
    fi
    
    # Start monitoring
    start_monitoring
    
    local restart_count=0
    
    while [ $restart_count -lt $MAX_RESTARTS ]; do
        log_message "${BLUE}📊 Attempt $((restart_count + 1))/$MAX_RESTARTS${NC}"
        
        # Start application
        start_application
        local app_pid=$!
        
        # Wait for health check
        if wait_for_health; then
            log_message "${GREEN}✅ Application started successfully${NC}"
            
            # Wait for the application to exit
            wait $app_pid
            local exit_code=$?
            
            log_message "${YELLOW}⚠️ Application exited with code $exit_code${NC}"
            
            # Check if this was a graceful shutdown
            if [ $exit_code -eq 0 ]; then
                log_message "${GREEN}✅ Graceful shutdown detected${NC}"
                break
            fi
            
            # Check if we should restart
            restart_count=$((restart_count + 1))
            
            if [ $restart_count -lt $MAX_RESTARTS ]; then
                log_message "${YELLOW}🔄 Restarting in ${RESTART_DELAY}s...${NC}"
                sleep $RESTART_DELAY
            fi
        else
            log_message "${RED}❌ Application failed to start properly${NC}"
            restart_count=$((restart_count + 1))
            
            # Kill the failed process
            kill $app_pid 2>/dev/null || true
            
            if [ $restart_count -lt $MAX_RESTARTS ]; then
                log_message "${YELLOW}🔄 Retrying in ${RESTART_DELAY}s...${NC}"
                sleep $RESTART_DELAY
            fi
        fi
    done
    
    if [ $restart_count -ge $MAX_RESTARTS ]; then
        log_message "${RED}❌ Maximum restart attempts reached. Giving up.${NC}"
        cleanup
        exit 1
    fi
    
    log_message "${GREEN}✅ Application completed successfully${NC}"
    cleanup
}

# Check if running as main script
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
