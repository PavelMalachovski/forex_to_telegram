
#!/bin/bash

# System monitoring script for Forex Bot
# This script monitors system resources and application performance

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
LOG_FILE="$LOG_DIR/monitor.log"
CHECK_INTERVAL=300  # 5 minutes
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=90

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to get CPU usage
get_cpu_usage() {
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}'
}

# Function to get memory usage
get_memory_usage() {
    free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}'
}

# Function to get disk usage
get_disk_usage() {
    df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Function to get application metrics
get_app_metrics() {
    local pid
    pid=$(pgrep -f "python.*production_scheduler.py")
    
    if [ -n "$pid" ]; then
        local app_cpu app_memory
        app_cpu=$(ps -p "$pid" -o %cpu --no-headers 2>/dev/null | tr -d ' ')
        app_memory=$(ps -p "$pid" -o %mem --no-headers 2>/dev/null | tr -d ' ')
        
        echo "App CPU: ${app_cpu:-0}%, App Memory: ${app_memory:-0}%"
    else
        echo "App not running"
    fi
}

# Function to check system health
check_system_health() {
    local cpu_usage memory_usage disk_usage
    
    cpu_usage=$(get_cpu_usage)
    memory_usage=$(get_memory_usage)
    disk_usage=$(get_disk_usage)
    
    log_message "System metrics - CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%"
    
    # Check thresholds
    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l) )); then
        log_message "WARNING: High CPU usage detected: ${cpu_usage}%"
    fi
    
    if (( $(echo "$memory_usage > $MEMORY_THRESHOLD" | bc -l) )); then
        log_message "WARNING: High memory usage detected: ${memory_usage}%"
    fi
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        log_message "WARNING: High disk usage detected: ${disk_usage}%"
    fi
    
    # Application metrics
    local app_metrics
    app_metrics=$(get_app_metrics)
    log_message "Application metrics - $app_metrics"
}

# Function to check log file sizes
check_log_sizes() {
    local log_size_mb
    
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            log_size_mb=$(du -m "$log_file" | cut -f1)
            if [ "$log_size_mb" -gt 100 ]; then  # 100MB threshold
                log_message "WARNING: Large log file detected: $log_file (${log_size_mb}MB)"
                
                # Rotate log file
                mv "$log_file" "${log_file}.old"
                touch "$log_file"
                log_message "Log file rotated: $log_file"
            fi
        fi
    done
}

# Function to check network connectivity
check_network() {
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        log_message "Network connectivity: OK"
    else
        log_message "WARNING: Network connectivity issues detected"
    fi
}

# Main monitoring loop
main() {
    log_message "System monitoring started for Forex Bot"
    
    while true; do
        check_system_health
        check_log_sizes
        check_network
        
        log_message "Monitoring cycle completed"
        sleep $CHECK_INTERVAL
    done
}

# Handle signals
trap 'log_message "Monitor stopping..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
