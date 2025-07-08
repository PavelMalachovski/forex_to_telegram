
"""Health monitoring utilities for the application."""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class HealthMetric:
    """Health metric data class."""
    name: str
    value: float
    timestamp: datetime
    status: str = "OK"  # OK, WARNING, CRITICAL
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    unit: str = ""
    description: str = ""


@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    check_func: Callable[[], HealthMetric]
    interval: float = 60.0  # seconds
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_result: Optional[HealthMetric] = None


class HealthMonitor:
    """Health monitoring system."""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.max_history_size = 1000
        
    def register_check(
        self,
        name: str,
        check_func: Callable[[], HealthMetric],
        interval: float = 60.0,
        enabled: bool = True
    ) -> None:
        """
        Register a health check.
        
        Args:
            name: Name of the health check
            check_func: Function that returns a HealthMetric
            interval: Check interval in seconds
            enabled: Whether the check is enabled
        """
        with self.lock:
            self.checks[name] = HealthCheck(
                name=name,
                check_func=check_func,
                interval=interval,
                enabled=enabled
            )
            
            if name not in self.metrics_history:
                self.metrics_history[name] = []
        
        logger.info(f"Registered health check: {name}")
    
    def start_monitoring(self) -> None:
        """Start the health monitoring thread."""
        if self.running:
            logger.warning("Health monitoring is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the health monitoring thread."""
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Health monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                with self.lock:
                    for check in self.checks.values():
                        if not check.enabled:
                            continue
                        
                        # Check if it's time to run this check
                        if (check.last_run is None or 
                            (current_time - check.last_run).total_seconds() >= check.interval):
                            
                            try:
                                metric = check.check_func()
                                check.last_run = current_time
                                check.last_result = metric
                                
                                # Store in history
                                self._store_metric(metric)
                                
                                # Log if status is not OK
                                if metric.status != "OK":
                                    logger.warning(f"Health check {metric.name}: {metric.status} - {metric.value}")
                                
                            except Exception as e:
                                logger.error(f"Error running health check {check.name}: {e}")
                                
                                # Create error metric
                                error_metric = HealthMetric(
                                    name=check.name,
                                    value=0.0,
                                    timestamp=current_time,
                                    status="CRITICAL",
                                    description=f"Check failed: {e}"
                                )
                                
                                check.last_result = error_metric
                                self._store_metric(error_metric)
                
                time.sleep(1.0)  # Check every second, but respect individual intervals
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(5.0)  # Wait before retrying
    
    def _store_metric(self, metric: HealthMetric) -> None:
        """Store metric in history."""
        if metric.name not in self.metrics_history:
            self.metrics_history[metric.name] = []
        
        history = self.metrics_history[metric.name]
        history.append(metric)
        
        # Trim history if too large
        if len(history) > self.max_history_size:
            history[:] = history[-self.max_history_size:]
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Get current health status.
        
        Returns:
            Dictionary with current health status
        """
        with self.lock:
            status = {
                'overall_status': 'OK',
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {},
                'summary': {
                    'total_checks': len(self.checks),
                    'enabled_checks': sum(1 for c in self.checks.values() if c.enabled),
                    'ok_checks': 0,
                    'warning_checks': 0,
                    'critical_checks': 0
                }
            }
            
            for name, check in self.checks.items():
                if not check.enabled:
                    continue
                
                check_status = {
                    'enabled': check.enabled,
                    'last_run': check.last_run.isoformat() if check.last_run else None,
                    'interval': check.interval,
                    'status': 'UNKNOWN'
                }
                
                if check.last_result:
                    result = check.last_result
                    check_status.update({
                        'status': result.status,
                        'value': result.value,
                        'unit': result.unit,
                        'description': result.description,
                        'timestamp': result.timestamp.isoformat()
                    })
                    
                    # Update summary counts
                    if result.status == 'OK':
                        status['summary']['ok_checks'] += 1
                    elif result.status == 'WARNING':
                        status['summary']['warning_checks'] += 1
                        if status['overall_status'] == 'OK':
                            status['overall_status'] = 'WARNING'
                    elif result.status == 'CRITICAL':
                        status['summary']['critical_checks'] += 1
                        status['overall_status'] = 'CRITICAL'
                
                status['checks'][name] = check_status
            
            return status
    
    def get_metrics_history(
        self,
        check_name: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[HealthMetric]:
        """
        Get metrics history for a specific check.
        
        Args:
            check_name: Name of the health check
            since: Only return metrics after this time
            limit: Maximum number of metrics to return
            
        Returns:
            List of HealthMetric objects
        """
        with self.lock:
            if check_name not in self.metrics_history:
                return []
            
            metrics = self.metrics_history[check_name]
            
            # Filter by time if specified
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            # Apply limit if specified
            if limit:
                metrics = metrics[-limit:]
            
            return metrics.copy()
    
    def run_check_now(self, check_name: str) -> Optional[HealthMetric]:
        """
        Run a specific health check immediately.
        
        Args:
            check_name: Name of the health check to run
            
        Returns:
            HealthMetric result or None if check not found
        """
        with self.lock:
            if check_name not in self.checks:
                logger.error(f"Health check not found: {check_name}")
                return None
            
            check = self.checks[check_name]
            
            try:
                metric = check.check_func()
                check.last_run = datetime.utcnow()
                check.last_result = metric
                
                self._store_metric(metric)
                
                logger.info(f"Manual health check {check_name}: {metric.status}")
                return metric
                
            except Exception as e:
                logger.error(f"Error running health check {check_name}: {e}")
                return None


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    
    return _health_monitor


# Built-in health checks
def memory_usage_check() -> HealthMetric:
    """Check memory usage."""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        status = "OK"
        if memory_mb > 800:
            status = "CRITICAL"
        elif memory_mb > 500:
            status = "WARNING"
        
        return HealthMetric(
            name="memory_usage",
            value=memory_mb,
            timestamp=datetime.utcnow(),
            status=status,
            threshold_warning=500.0,
            threshold_critical=800.0,
            unit="MB",
            description=f"Process memory usage: {memory_mb:.1f} MB"
        )
        
    except ImportError:
        return HealthMetric(
            name="memory_usage",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="WARNING",
            description="psutil not available"
        )
    except Exception as e:
        return HealthMetric(
            name="memory_usage",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="CRITICAL",
            description=f"Error checking memory: {e}"
        )


def disk_usage_check() -> HealthMetric:
    """Check disk usage."""
    try:
        import psutil
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / 1024 / 1024 / 1024
        
        status = "OK"
        if free_gb < 0.5:
            status = "CRITICAL"
        elif free_gb < 1.0:
            status = "WARNING"
        
        return HealthMetric(
            name="disk_usage",
            value=free_gb,
            timestamp=datetime.utcnow(),
            status=status,
            threshold_warning=1.0,
            threshold_critical=0.5,
            unit="GB",
            description=f"Free disk space: {free_gb:.1f} GB"
        )
        
    except ImportError:
        return HealthMetric(
            name="disk_usage",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="WARNING",
            description="psutil not available"
        )
    except Exception as e:
        return HealthMetric(
            name="disk_usage",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="CRITICAL",
            description=f"Error checking disk: {e}"
        )


def uptime_check() -> HealthMetric:
    """Check application uptime."""
    try:
        import psutil
        process = psutil.Process()
        uptime_seconds = time.time() - process.create_time()
        uptime_hours = uptime_seconds / 3600
        
        return HealthMetric(
            name="uptime",
            value=uptime_hours,
            timestamp=datetime.utcnow(),
            status="OK",
            unit="hours",
            description=f"Application uptime: {uptime_hours:.1f} hours"
        )
        
    except ImportError:
        return HealthMetric(
            name="uptime",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="WARNING",
            description="psutil not available"
        )
    except Exception as e:
        return HealthMetric(
            name="uptime",
            value=0.0,
            timestamp=datetime.utcnow(),
            status="CRITICAL",
            description=f"Error checking uptime: {e}"
        )


def register_default_health_checks() -> None:
    """Register default health checks."""
    monitor = get_health_monitor()
    
    monitor.register_check("memory_usage", memory_usage_check, interval=30.0)
    monitor.register_check("disk_usage", disk_usage_check, interval=60.0)
    monitor.register_check("uptime", uptime_check, interval=300.0)
    
    logger.info("Default health checks registered")
