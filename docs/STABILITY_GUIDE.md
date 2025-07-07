
# Forex Bot Stability and Monitoring Guide

This guide covers the enhanced stability features, monitoring capabilities, and operational procedures for the Forex Bot application.

## Overview

The enhanced version includes:
- **Graceful signal handling** with state preservation
- **Comprehensive health monitoring** with metrics
- **Advanced logging** with rotation and structured output
- **Automatic restart mechanisms** via systemd
- **Monitoring scripts** for continuous oversight
- **Health check endpoints** for external monitoring

## Quick Start

### 1. Install Enhanced Dependencies

```bash
cd /home/ubuntu/forex_bot_postgresql
pip3 install -r requirements_enhanced.txt
```

### 2. Install as System Service

```bash
sudo ./scripts/install_service.sh install
```

### 3. Check Service Status

```bash
sudo systemctl status forex_bot
./scripts/health_check.sh
```

## Enhanced Features

### Signal Handling

The application now handles signals gracefully:

- **SIGTERM/SIGINT**: Initiates graceful shutdown
- **State preservation**: Saves application state before exit
- **Cleanup callbacks**: Ensures proper resource cleanup
- **Timeout protection**: Forces exit if cleanup takes too long

#### Protected Critical Sections

Critical operations (initialization/finalization) are protected from interruption:

```python
from app.utils.signal_handler import protect_critical_section

with protect_critical_section():
    # Critical initialization code
    initialize_database()
    setup_bot()
```

### Health Monitoring

Comprehensive health checks monitor:

- **System resources**: CPU, memory, disk usage
- **Database connectivity**: Connection and response time
- **External services**: API availability
- **Application health**: Bot status, error rates
- **Log health**: Error/warning counts

#### Health Endpoints

- `GET /health` - Basic health status
- `GET /health/detailed` - Comprehensive health report
- `GET /metrics` - Prometheus-style metrics

#### Custom Health Checks

Register custom health checks:

```python
from app.utils.health_monitor import register_health_check

def my_custom_check():
    # Your check logic
    return True, "Check passed", {"detail": "value"}

register_health_check("my_check", my_custom_check, "Description")
```

### Enhanced Logging

Advanced logging features:

- **Rotating file handlers**: Automatic log rotation
- **Structured logging**: JSON format for parsing
- **Context logging**: Add request/user context
- **Health-aware logging**: Track error rates
- **Multiple log levels**: Separate files for errors

#### Log Files

- `logs/app.log` - Main application log (rotated)
- `logs/error.log` - Error-only log (rotated)
- `logs/app_structured.log` - JSON structured log (daily rotation)
- `logs/health.log` - Health monitoring log

#### Context Logging

```python
from app.utils.enhanced_logging import log_with_context, log_event

# Add context to log messages
with log_with_context(logger, user_id="12345", request_id="req-abc"):
    logger.info("Processing user request")

# Log structured events
log_event(logger, "user_login", "User logged in", 
          user_id="12345", ip="192.168.1.1")
```

## Service Management

### Systemd Service

The application runs as a systemd service with:

- **Automatic restart**: `Restart=on-failure`
- **Resource limits**: Memory and CPU quotas
- **Security**: Restricted permissions
- **Health checks**: Post-start validation

#### Service Commands

```bash
# Service control
sudo systemctl start forex_bot
sudo systemctl stop forex_bot
sudo systemctl restart forex_bot
sudo systemctl status forex_bot

# View logs
journalctl -u forex_bot -f
journalctl -u forex_bot --since "1 hour ago"
```

### Configuration

Service configuration in `forex_bot.service`:

```ini
[Service]
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
MemoryMax=1G
CPUQuota=80%
```

## Monitoring and Alerting

### Health Check Script

Manual health checks:

```bash
# Basic health check
./scripts/health_check.sh

# Health check with auto-restart
./scripts/health_check.sh --restart

# Detailed health information
./scripts/health_check.sh --detailed
```

### Continuous Monitoring

Start continuous monitoring:

```bash
# Start monitor daemon
./scripts/monitor.sh start

# Check monitor status
./scripts/monitor.sh status

# View monitor logs
./scripts/monitor.sh logs -n 100

# Stop monitoring
./scripts/monitor.sh stop
```

### Automated Monitoring

Cron job runs health checks every 5 minutes:

```bash
# View cron health logs
tail -f logs/cron_health.log

# Edit cron schedule
crontab -e
```

## Troubleshooting

### Common Issues

#### Service Won't Start

1. Check service status:
   ```bash
   sudo systemctl status forex_bot
   ```

2. Check logs:
   ```bash
   journalctl -u forex_bot --since "10 minutes ago"
   ```

3. Check configuration:
   ```bash
   python3 enhanced_main.py  # Test manually
   ```

#### Health Checks Failing

1. Check detailed health:
   ```bash
   ./scripts/health_check.sh --detailed
   ```

2. Check individual components:
   ```bash
   curl http://localhost:5000/health/detailed | jq
   ```

3. Check system resources:
   ```bash
   htop
   df -h
   ```

#### High Resource Usage

1. Check resource limits:
   ```bash
   systemctl show forex_bot | grep -E "(Memory|CPU)"
   ```

2. Monitor resource usage:
   ```bash
   curl http://localhost:5000/metrics | grep system_
   ```

3. Adjust service limits in `forex_bot.service`

### Log Analysis

#### Find Errors

```bash
# Recent errors
grep -i error logs/app.log | tail -20

# Error patterns
grep -E "(ERROR|CRITICAL)" logs/app.log | cut -d' ' -f1-3 | sort | uniq -c

# Health issues
grep "Health check FAILED" logs/monitor.log
```

#### Performance Analysis

```bash
# Response times
grep "response_time_ms" logs/app_structured.log | jq '.response_time_ms'

# Error rates
grep "error_count" logs/health.log
```

## Performance Optimization

### Resource Tuning

1. **Memory limits**: Adjust `MemoryMax` in service file
2. **CPU limits**: Adjust `CPUQuota` in service file
3. **Log rotation**: Configure rotation frequency
4. **Health check interval**: Adjust monitoring frequency

### Database Optimization

1. **Connection pooling**: Configure in `config.py`
2. **Query optimization**: Monitor slow queries
3. **Index maintenance**: Regular database maintenance

### Monitoring Overhead

1. **Health check frequency**: Balance monitoring vs. performance
2. **Log verbosity**: Adjust log levels for production
3. **Metrics collection**: Disable unused metrics

## Security Considerations

### Service Security

The systemd service includes security hardening:

- `NoNewPrivileges=true`
- `ProtectSystem=strict`
- `ProtectHome=true`
- `PrivateTmp=true`

### Log Security

- Logs are written with restricted permissions
- Sensitive data is filtered from logs
- Log rotation prevents disk exhaustion

### Network Security

- Health endpoints can be restricted by IP
- API endpoints require authentication
- Webhook URLs use HTTPS

## Backup and Recovery

### State Preservation

Application state is automatically saved:

- `logs/app_state.json` - Last application state
- Automatic recovery on restart
- Graceful shutdown state saving

### Log Backup

Logs are automatically rotated and compressed:

- Daily rotation for structured logs
- Size-based rotation for application logs
- Configurable retention periods

### Database Backup

Regular database backups recommended:

```bash
# PostgreSQL backup
pg_dump forex_bot > backup_$(date +%Y%m%d).sql

# Restore
psql forex_bot < backup_20240101.sql
```

## Integration with External Monitoring

### Prometheus Integration

Metrics endpoint compatible with Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'forex-bot'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboards

Create dashboards using metrics:

- `app_health_status` - Overall health
- `system_cpu_percent` - CPU usage
- `system_memory_percent` - Memory usage
- `health_check_duration_ms` - Check performance

### External Alerting

Configure alerts based on health endpoints:

```bash
# Example: Nagios check
check_http -H localhost -p 5000 -u /health -s "healthy"

# Example: Uptime monitoring
curl -f http://localhost:5000/health || alert
```

## Maintenance Procedures

### Regular Maintenance

1. **Weekly**: Review logs for errors
2. **Monthly**: Check disk usage and log rotation
3. **Quarterly**: Update dependencies
4. **Annually**: Review security settings

### Update Procedure

1. Stop service:
   ```bash
   sudo systemctl stop forex_bot
   ```

2. Update code and dependencies:
   ```bash
   git pull
   pip3 install -r requirements_enhanced.txt
   ```

3. Test configuration:
   ```bash
   python3 enhanced_main.py --test
   ```

4. Start service:
   ```bash
   sudo systemctl start forex_bot
   ```

5. Verify health:
   ```bash
   ./scripts/health_check.sh
   ```

## Support and Debugging

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or modify config.py
LOG_LEVEL = "DEBUG"
```

### Diagnostic Information

Collect diagnostic information:

```bash
# System info
./scripts/health_check.sh --detailed > diagnostic_$(date +%Y%m%d).json

# Service info
systemctl status forex_bot > service_status.txt
journalctl -u forex_bot --since "1 day ago" > service_logs.txt

# Health report
curl http://localhost:5000/health/detailed | jq > health_report.json
```

### Getting Help

When reporting issues, include:

1. Service status output
2. Recent log entries
3. Health check results
4. System resource usage
5. Configuration details (without secrets)

---

For additional support or questions, refer to the project documentation or contact the development team.
