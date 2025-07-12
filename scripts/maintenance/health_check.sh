
#!/bin/bash

# Health check script for Forex Bot
# This script checks if the application is running and responding

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
LOG_FILE="$LOG_DIR/health_check.log"
API_URL="http://localhost:8000"
TIMEOUT=10

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check API health
check_api_health() {
    local response
    response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$API_URL/health" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        log_message "API health check: PASSED"
        return 0
    else
        log_message "API health check: FAILED (HTTP $response)"
        return 1
    fi
}

# Function to check process
check_process() {
    if pgrep -f "python.*production_scheduler.py" > /dev/null; then
        log_message "Process check: PASSED"
        return 0
    else
        log_message "Process check: FAILED"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    cd "$PROJECT_DIR"
    if python -c "
import sys
sys.path.insert(0, '.')
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
if db.test_connection():
    print('Database check: PASSED')
    exit(0)
else:
    print('Database check: FAILED')
    exit(1)
" 2>/dev/null; then
        log_message "Database check: PASSED"
        return 0
    else
        log_message "Database check: FAILED"
        return 1
    fi
}

# Main health check
main() {
    log_message "Starting health check..."
    
    local exit_code=0
    
    # Check process
    if ! check_process; then
        exit_code=1
    fi
    
    # Check API
    if ! check_api_health; then
        exit_code=1
    fi
    
    # Check database
    if ! check_database; then
        exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        log_message "Health check: ALL CHECKS PASSED"
    else
        log_message "Health check: SOME CHECKS FAILED"
    fi
    
    return $exit_code
}

# Run main function
main "$@"
