
#!/bin/bash

# Installation script for Forex Bot systemd service

set -euo pipefail

# Configuration
SERVICE_NAME="forex_bot"
SERVICE_FILE="forex_bot.service"
# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${BLUE}[INSTALL]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install required packages
install_dependencies() {
    log "Installing required packages..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        jq \
        mailutils \
        logrotate
    
    success "Dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        success "Python dependencies installed"
    else
        warning "requirements.txt not found, skipping Python dependencies"
    fi
}

# Create systemd service
install_service() {
    log "Installing systemd service..."
    
    # Check if service file exists
    if [ ! -f "$PROJECT_DIR/$SERVICE_FILE" ]; then
        error "Service file $SERVICE_FILE not found in $PROJECT_DIR"
        exit 1
    fi
    
    # Copy service file
    cp "$PROJECT_DIR/$SERVICE_FILE" "/etc/systemd/system/"
    
    # Set proper permissions
    chmod 644 "/etc/systemd/system/$SERVICE_FILE"
    
    # Reload systemd
    systemctl daemon-reload
    
    success "Service file installed"
}

# Setup log rotation
setup_logrotate() {
    log "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload-or-restart $SERVICE_NAME.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    success "Log rotation configured"
}

# Setup monitoring cron job
setup_monitoring() {
    log "Setting up monitoring cron job..."
    
    # Make scripts executable
    chmod +x "$SCRIPTS_DIR"/*.sh
    
    # Add cron job for health monitoring
    crontab -u ubuntu -l 2>/dev/null | grep -v "$SCRIPTS_DIR/health_check.sh" > /tmp/crontab_new || true
    echo "*/5 * * * * $SCRIPTS_DIR/health_check.sh --restart >> $PROJECT_DIR/logs/cron_health.log 2>&1" >> /tmp/crontab_new
    crontab -u ubuntu /tmp/crontab_new
    rm /tmp/crontab_new
    
    success "Monitoring cron job configured"
}

# Create necessary directories and set permissions
setup_directories() {
    log "Setting up directories and permissions..."
    
    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"
    
    # Set ownership
    chown -R ubuntu:ubuntu "$PROJECT_DIR"
    
    # Set permissions
    chmod -R 755 "$PROJECT_DIR"
    chmod -R 644 "$PROJECT_DIR/logs"
    
    success "Directories and permissions configured"
}

# Enable and start service
enable_service() {
    log "Enabling and starting service..."
    
    # Enable service
    systemctl enable "$SERVICE_NAME.service"
    
    # Start service
    systemctl start "$SERVICE_NAME.service"
    
    # Wait a moment for service to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME.service"; then
        success "Service started successfully"
    else
        error "Service failed to start"
        systemctl status "$SERVICE_NAME.service"
        exit 1
    fi
}

# Show service status
show_status() {
    log "Service status:"
    systemctl status "$SERVICE_NAME.service" --no-pager
    
    echo ""
    log "Service logs (last 20 lines):"
    journalctl -u "$SERVICE_NAME.service" -n 20 --no-pager
    
    echo ""
    log "Health check:"
    if sudo -u ubuntu "$SCRIPTS_DIR/health_check.sh"; then
        success "Health check passed"
    else
        warning "Health check failed"
    fi
}

# Uninstall service
uninstall_service() {
    log "Uninstalling service..."
    
    # Stop and disable service
    systemctl stop "$SERVICE_NAME.service" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME.service" 2>/dev/null || true
    
    # Remove service file
    rm -f "/etc/systemd/system/$SERVICE_FILE"
    
    # Remove logrotate config
    rm -f "/etc/logrotate.d/$SERVICE_NAME"
    
    # Remove cron job
    crontab -u ubuntu -l 2>/dev/null | grep -v "$SCRIPTS_DIR/health_check.sh" | crontab -u ubuntu - || true
    
    # Reload systemd
    systemctl daemon-reload
    
    success "Service uninstalled"
}

# Main installation function
install() {
    log "Starting Forex Bot service installation..."
    
    check_root
    install_dependencies
    install_python_deps
    setup_directories
    install_service
    setup_logrotate
    setup_monitoring
    enable_service
    show_status
    
    success "Installation completed successfully!"
    echo ""
    echo "Service management commands:"
    echo "  sudo systemctl start $SERVICE_NAME      # Start service"
    echo "  sudo systemctl stop $SERVICE_NAME       # Stop service"
    echo "  sudo systemctl restart $SERVICE_NAME    # Restart service"
    echo "  sudo systemctl status $SERVICE_NAME     # Check status"
    echo "  journalctl -u $SERVICE_NAME -f          # Follow logs"
    echo ""
    echo "Monitoring commands:"
    echo "  $SCRIPTS_DIR/health_check.sh            # Manual health check"
    echo "  $SCRIPTS_DIR/monitor.sh start           # Start continuous monitoring"
    echo "  $SCRIPTS_DIR/monitor.sh status          # Check monitor status"
}

# Show usage
usage() {
    echo "Usage: $0 {install|uninstall|status|help}"
    echo ""
    echo "Commands:"
    echo "  install     Install and configure the service"
    echo "  uninstall   Remove the service and configuration"
    echo "  status      Show current service status"
    echo "  help        Show this help message"
}

# Main script logic
case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        check_root
        uninstall_service
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
