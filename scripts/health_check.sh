
#!/bin/bash

# Health check script for Forex Bot
# Can be used by monitoring systems or cron jobs

set -euo pipefail

# Configuration
HEALTH_URL="http://localhost:5000/health"
DETAILED_HEALTH_URL="http://localhost:5000/health/detailed"
TIMEOUT=10
LOG_FILE="/home/ubuntu/forex_bot_postgresql/logs/health_check.log"
ALERT_EMAIL=""  # Set email for alerts
MAX_RETRIES=3
RETRY_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if service is running
check_service_status() {
    if systemctl is-active --quiet forex_bot.service; then
        log "✓ Service is running"
        return 0
    else
        log "✗ Service is not running"
        return 1
    fi
}

# Check health endpoint
check_health_endpoint() {
    local url="$1"
    local description="$2"
    
    log "Checking $description..."
    
    if response=$(curl -s -f --max-time "$TIMEOUT" "$url" 2>/dev/null); then
        status=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [ "$status" = "healthy" ]; then
            log "✓ $description: HEALTHY"
            return 0
        else
            log "✗ $description: UNHEALTHY (status: $status)"
            return 1
        fi
    else
        log "✗ $description: UNREACHABLE"
        return 1
    fi
}

# Check detailed health with retries
check_detailed_health() {
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if response=$(curl -s --max-time "$TIMEOUT" "$DETAILED_HEALTH_URL" 2>/dev/null); then
            echo "$response" | jq '.' > "/tmp/health_detailed_$(date +%s).json" 2>/dev/null || true
            
            # Extract key metrics
            overall_status=$(echo "$response" | jq -r '.overall_status // "unknown"' 2>/dev/null || echo "unknown")
            uptime=$(echo "$response" | jq -r '.uptime_seconds // 0' 2>/dev/null || echo "0")
            total_checks=$(echo "$response" | jq -r '.summary.total_checks // 0' 2>/dev/null || echo "0")
            healthy_checks=$(echo "$response" | jq -r '.summary.healthy_checks // 0' 2>/dev/null || echo "0")
            
            log "Detailed health check - Status: $overall_status, Uptime: ${uptime}s, Checks: $healthy_checks/$total_checks"
            
            if [ "$overall_status" = "healthy" ]; then
                return 0
            else
                log "Detailed health check failed - Status: $overall_status"
                return 1
            fi
        else
            retries=$((retries + 1))
            if [ $retries -lt $MAX_RETRIES ]; then
                log "Detailed health check failed, retrying in ${RETRY_DELAY}s... (attempt $retries/$MAX_RETRIES)"
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    log "Detailed health check failed after $MAX_RETRIES attempts"
    return 1
}

# Send alert (if email configured)
send_alert() {
    local subject="$1"
    local message="$2"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || true
        log "Alert sent to $ALERT_EMAIL"
    fi
}

# Restart service if needed
restart_service() {
    log "Attempting to restart forex_bot service..."
    
    if sudo systemctl restart forex_bot.service; then
        log "Service restart initiated"
        sleep 15  # Wait for service to start
        
        if check_service_status && check_health_endpoint "$HEALTH_URL" "Basic health"; then
            log "Service restart successful"
            send_alert "Forex Bot - Service Restarted" "The forex bot service was automatically restarted and is now healthy."
            return 0
        else
            log "Service restart failed - service still unhealthy"
            return 1
        fi
    else
        log "Failed to restart service"
        return 1
    fi
}

# Main health check function
main() {
    local exit_code=0
    local issues=()
    
    log "=== Starting health check ==="
    
    # Check if service is running
    if ! check_service_status; then
        issues+=("Service not running")
        exit_code=1
    fi
    
    # Check basic health endpoint
    if ! check_health_endpoint "$HEALTH_URL" "Basic health"; then
        issues+=("Basic health check failed")
        exit_code=1
    fi
    
    # Check detailed health
    if ! check_detailed_health; then
        issues+=("Detailed health check failed")
        exit_code=1
    fi
    
    # If there are issues, try to restart (if --restart flag is provided)
    if [ $exit_code -ne 0 ] && [ "${1:-}" = "--restart" ]; then
        log "Health check failed, attempting automatic restart..."
        
        if restart_service; then
            exit_code=0
            issues=()
        else
            issues+=("Automatic restart failed")
        fi
    fi
    
    # Summary
    if [ $exit_code -eq 0 ]; then
        log "=== Health check PASSED ==="
        echo -e "${GREEN}✓ All health checks passed${NC}"
    else
        log "=== Health check FAILED ==="
        echo -e "${RED}✗ Health check failed: ${issues[*]}${NC}"
        
        send_alert "Forex Bot - Health Check Failed" "Health check failed with issues: ${issues[*]}"
    fi
    
    log "=== Health check completed ==="
    return $exit_code
}

# Show usage
usage() {
    echo "Usage: $0 [--restart] [--detailed] [--help]"
    echo ""
    echo "Options:"
    echo "  --restart   Automatically restart service if health check fails"
    echo "  --detailed  Show detailed health information"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Basic health check"
    echo "  $0 --restart         # Health check with auto-restart"
    echo "  $0 --detailed        # Show detailed health info"
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        usage
        exit 0
        ;;
    --detailed)
        if response=$(curl -s --max-time "$TIMEOUT" "$DETAILED_HEALTH_URL" 2>/dev/null); then
            echo "$response" | jq '.' 2>/dev/null || echo "$response"
        else
            echo "Failed to get detailed health information"
            exit 1
        fi
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
