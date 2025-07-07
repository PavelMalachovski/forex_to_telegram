
#!/bin/bash

# Render Resource Check Script
# Monitors resource usage and provides warnings for Render.com deployment

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CHECK_INTERVAL=${CHECK_INTERVAL:-30}
LOG_FILE=${LOG_FILE:-"/home/ubuntu/forex_bot_postgresql/logs/resource_check.log"}
MEMORY_WARNING_THRESHOLD=${MEMORY_WARNING_THRESHOLD:-80}
MEMORY_CRITICAL_THRESHOLD=${MEMORY_CRITICAL_THRESHOLD:-90}
CPU_WARNING_THRESHOLD=${CPU_WARNING_THRESHOLD:-80}
CPU_CRITICAL_THRESHOLD=${CPU_CRITICAL_THRESHOLD:-95}

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    local message="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    echo -e "[$timestamp] $message" | tee -a "$LOG_FILE"
}

get_memory_usage() {
    # Get memory usage percentage
    free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}'
}

get_cpu_usage() {
    # Get CPU usage percentage (1 second average)
    top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}'
}

get_process_memory() {
    # Get memory usage of current process tree
    local pid=${1:-$$}
    ps -o pid,ppid,rss,vsz,pcpu,pmem,comm -p $pid 2>/dev/null | tail -n +2
}

check_render_environment() {
    log_message "${BLUE}🔍 Checking Render Environment${NC}"
    
    if [ -n "$RENDER_EXTERNAL_HOSTNAME" ]; then
        log_message "${GREEN}✅ Running on Render: $RENDER_EXTERNAL_HOSTNAME${NC}"
        log_message "Service: ${RENDER_SERVICE_NAME:-unknown}"
        log_message "Service ID: ${RENDER_SERVICE_ID:-unknown}"
        log_message "Git Commit: ${RENDER_GIT_COMMIT:-unknown}"
        log_message "Port: ${PORT:-10000}"
    else
        log_message "${YELLOW}⚠️ Not running on Render (local environment)${NC}"
    fi
}

check_system_resources() {
    local memory_usage=$(get_memory_usage)
    local cpu_usage=$(get_cpu_usage)
    
    log_message "${BLUE}📊 System Resources${NC}"
    log_message "Memory Usage: ${memory_usage}%"
    log_message "CPU Usage: ${cpu_usage}%"
    
    # Memory checks
    if (( $(echo "$memory_usage > $MEMORY_CRITICAL_THRESHOLD" | bc -l) )); then
        log_message "${RED}🚨 CRITICAL: Memory usage ${memory_usage}% > ${MEMORY_CRITICAL_THRESHOLD}%${NC}"
        return 1
    elif (( $(echo "$memory_usage > $MEMORY_WARNING_THRESHOLD" | bc -l) )); then
        log_message "${YELLOW}⚠️ WARNING: Memory usage ${memory_usage}% > ${MEMORY_WARNING_THRESHOLD}%${NC}"
    else
        log_message "${GREEN}✅ Memory usage OK: ${memory_usage}%${NC}"
    fi
    
    # CPU checks
    if (( $(echo "$cpu_usage > $CPU_CRITICAL_THRESHOLD" | bc -l) )); then
        log_message "${RED}🚨 CRITICAL: CPU usage ${cpu_usage}% > ${CPU_CRITICAL_THRESHOLD}%${NC}"
        return 1
    elif (( $(echo "$cpu_usage > $CPU_WARNING_THRESHOLD" | bc -l) )); then
        log_message "${YELLOW}⚠️ WARNING: CPU usage ${cpu_usage}% > ${CPU_WARNING_THRESHOLD}%${NC}"
    else
        log_message "${GREEN}✅ CPU usage OK: ${cpu_usage}%${NC}"
    fi
    
    return 0
}

check_process_resources() {
    log_message "${BLUE}🔍 Process Resources${NC}"
    
    # Find Python processes
    local python_pids=$(pgrep -f "python.*enhanced_main.py" || echo "")
    
    if [ -n "$python_pids" ]; then
        for pid in $python_pids; do
            log_message "Python process PID: $pid"
            get_process_memory $pid | while read line; do
                log_message "  $line"
            done
            
            # Check if process memory is approaching limits
            local rss_kb=$(ps -o rss= -p $pid 2>/dev/null | tr -d ' ')
            if [ -n "$rss_kb" ]; then
                local rss_mb=$((rss_kb / 1024))
                log_message "Process memory: ${rss_mb}MB"
                
                if [ $rss_mb -gt 480 ]; then
                    log_message "${RED}🚨 CRITICAL: Process memory ${rss_mb}MB approaching 512MB limit${NC}"
                elif [ $rss_mb -gt 400 ]; then
                    log_message "${YELLOW}⚠️ WARNING: Process memory ${rss_mb}MB getting high${NC}"
                else
                    log_message "${GREEN}✅ Process memory OK: ${rss_mb}MB${NC}"
                fi
            fi
        done
    else
        log_message "${YELLOW}⚠️ No Python processes found${NC}"
    fi
}

check_disk_usage() {
    log_message "${BLUE}💾 Disk Usage${NC}"
    
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    log_message "Disk usage: ${disk_usage}%"
    
    if [ $disk_usage -gt 90 ]; then
        log_message "${RED}🚨 CRITICAL: Disk usage ${disk_usage}% > 90%${NC}"
    elif [ $disk_usage -gt 80 ]; then
        log_message "${YELLOW}⚠️ WARNING: Disk usage ${disk_usage}% > 80%${NC}"
    else
        log_message "${GREEN}✅ Disk usage OK: ${disk_usage}%${NC}"
    fi
}

check_network_connectivity() {
    log_message "${BLUE}🌐 Network Connectivity${NC}"
    
    # Check if we can reach external services
    if curl -s --max-time 5 https://api.telegram.org > /dev/null; then
        log_message "${GREEN}✅ Telegram API reachable${NC}"
    else
        log_message "${RED}❌ Telegram API unreachable${NC}"
    fi
    
    # Check if health endpoint is responding (if running)
    local port=${PORT:-10000}
    if curl -s --max-time 5 "http://localhost:$port/health" > /dev/null; then
        log_message "${GREEN}✅ Health endpoint responding on port $port${NC}"
    else
        log_message "${YELLOW}⚠️ Health endpoint not responding on port $port${NC}"
    fi
}

check_application_logs() {
    log_message "${BLUE}📋 Recent Application Logs${NC}"
    
    local app_log="/home/ubuntu/forex_bot_postgresql/logs/enhanced_app.log"
    if [ -f "$app_log" ]; then
        log_message "Last 5 lines from application log:"
        tail -5 "$app_log" | while read line; do
            log_message "  $line"
        done
        
        # Check for error patterns
        local recent_errors=$(tail -100 "$app_log" | grep -i "error\|critical\|sigterm" | wc -l)
        if [ $recent_errors -gt 0 ]; then
            log_message "${YELLOW}⚠️ Found $recent_errors recent error/critical/sigterm entries${NC}"
        fi
    else
        log_message "${YELLOW}⚠️ Application log not found: $app_log${NC}"
    fi
}

run_health_check() {
    log_message "${BLUE}🏥 Running Health Check${NC}"
    
    local port=${PORT:-10000}
    local health_response=$(curl -s --max-time 10 "http://localhost:$port/health" || echo "")
    
    if [ -n "$health_response" ]; then
        log_message "${GREEN}✅ Health check successful${NC}"
        echo "$health_response" | jq . 2>/dev/null || echo "$health_response"
    else
        log_message "${RED}❌ Health check failed${NC}"
        return 1
    fi
}

main() {
    log_message "${GREEN}🚀 Starting Render Resource Check${NC}"
    log_message "Check interval: ${CHECK_INTERVAL} seconds"
    log_message "Log file: $LOG_FILE"
    
    # Initial checks
    check_render_environment
    
    # Main monitoring loop
    while true; do
        log_message "${BLUE}==================== Resource Check ====================${NC}"
        
        local exit_code=0
        
        check_system_resources || exit_code=1
        check_process_resources
        check_disk_usage
        check_network_connectivity
        check_application_logs
        
        # Run health check if application is running
        if pgrep -f "python.*enhanced_main.py" > /dev/null; then
            run_health_check || exit_code=1
        fi
        
        if [ $exit_code -eq 0 ]; then
            log_message "${GREEN}✅ All checks passed${NC}"
        else
            log_message "${RED}❌ Some checks failed - investigate immediately${NC}"
        fi
        
        log_message "${BLUE}======================================================${NC}"
        
        # Exit on critical conditions if requested
        if [ "$EXIT_ON_CRITICAL" = "true" ] && [ $exit_code -eq 1 ]; then
            log_message "${RED}🚨 Exiting due to critical conditions${NC}"
            exit 1
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Handle signals
trap 'log_message "Resource check interrupted"; exit 0' INT TERM

# Check if running as main script
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
