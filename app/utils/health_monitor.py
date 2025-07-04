
"""
Comprehensive health monitoring system with checks and metrics.
"""

import logging
import psutil
import time
import threading
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from app.config import config
from app.database.connection import SessionLocal

logger = logging.getLogger("health")

@dataclass
class HealthCheck:
    """Represents a single health check result."""
    name: str
    status: str  # "healthy", "unhealthy", "warning"
    message: str
    timestamp: str
    duration_ms: float
    details: Dict[str, Any] = None

@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float
    load_average: List[float]
    uptime_seconds: float

class HealthMonitor:
    """
    Comprehensive health monitoring system.
    Performs various health checks and tracks system metrics.
    """
    
    def __init__(self):
        self.checks = {}
        self.metrics_history = []
        self.max_history_size = 100
        self.last_check_time = None
        self.check_interval = 30  # seconds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 90.0,
            'response_time_warning': 1000,  # ms
            'response_time_critical': 5000,  # ms
        }
        self._lock = threading.Lock()
        self.start_time = time.time()
        
        logger.info("HealthMonitor initialized")
    
    def register_check(self, name: str, check_func: Callable[[], tuple], 
                      description: str = ""):
        """
        Register a custom health check function.
        
        Args:
            name: Unique name for the check
            check_func: Function that returns (is_healthy: bool, message: str, details: dict)
            description: Human-readable description of the check
        """
        self.checks[name] = {
            'func': check_func,
            'description': description,
            'last_result': None
        }
        logger.info(f"Registered health check: {name}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Load average (Unix-like systems)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]  # Windows doesn't have load average
            
            # Uptime
            uptime_seconds = time.time() - self.start_time
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                load_average=load_average,
                uptime_seconds=uptime_seconds
            )
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            raise
    
    def check_database_health(self) -> tuple:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            db = SessionLocal()
            
            try:
                # Simple connectivity test
                result = db.execute("SELECT 1").scalar()
                if result != 1:
                    return False, "Database query returned unexpected result", {}
                
                # Check response time
                response_time = (time.time() - start_time) * 1000
                
                details = {
                    'response_time_ms': response_time,
                    'database_url': config.DATABASE_URL.split('@')[0] + '@***'  # Hide credentials
                }
                
                if response_time > self.thresholds['response_time_critical']:
                    return False, f"Database response time too high: {response_time:.2f}ms", details
                elif response_time > self.thresholds['response_time_warning']:
                    return True, f"Database response time elevated: {response_time:.2f}ms", details
                else:
                    return True, f"Database healthy (response: {response_time:.2f}ms)", details
                    
            finally:
                db.close()
                
        except Exception as e:
            return False, f"Database connection failed: {str(e)}", {'error': str(e)}
    
    def check_external_services(self) -> tuple:
        """Check external service dependencies."""
        services_to_check = [
            ('ForexFactory', 'https://www.forexfactory.com'),
            ('Google', 'https://www.google.com'),  # Basic internet connectivity
        ]
        
        results = {}
        overall_healthy = True
        messages = []
        
        for service_name, url in services_to_check:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; HealthCheck/1.0)'
                })
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    results[service_name] = {
                        'status': 'healthy',
                        'response_time_ms': response_time,
                        'status_code': response.status_code
                    }
                    messages.append(f"{service_name}: OK ({response_time:.0f}ms)")
                else:
                    results[service_name] = {
                        'status': 'unhealthy',
                        'response_time_ms': response_time,
                        'status_code': response.status_code
                    }
                    messages.append(f"{service_name}: HTTP {response.status_code}")
                    overall_healthy = False
                    
            except Exception as e:
                results[service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                messages.append(f"{service_name}: {str(e)}")
                overall_healthy = False
        
        message = "; ".join(messages)
        return overall_healthy, message, results
    
    def check_system_resources(self) -> tuple:
        """Check system resource usage."""
        try:
            metrics = self.get_system_metrics()
            issues = []
            warnings = []
            
            # Check CPU
            if metrics.cpu_percent > self.thresholds['cpu_critical']:
                issues.append(f"CPU usage critical: {metrics.cpu_percent:.1f}%")
            elif metrics.cpu_percent > self.thresholds['cpu_warning']:
                warnings.append(f"CPU usage high: {metrics.cpu_percent:.1f}%")
            
            # Check Memory
            if metrics.memory_percent > self.thresholds['memory_critical']:
                issues.append(f"Memory usage critical: {metrics.memory_percent:.1f}%")
            elif metrics.memory_percent > self.thresholds['memory_warning']:
                warnings.append(f"Memory usage high: {metrics.memory_percent:.1f}%")
            
            # Check Disk
            if metrics.disk_percent > self.thresholds['disk_critical']:
                issues.append(f"Disk usage critical: {metrics.disk_percent:.1f}%")
            elif metrics.disk_percent > self.thresholds['disk_warning']:
                warnings.append(f"Disk usage high: {metrics.disk_percent:.1f}%")
            
            # Determine overall status
            if issues:
                return False, f"Critical issues: {'; '.join(issues)}", asdict(metrics)
            elif warnings:
                return True, f"Warnings: {'; '.join(warnings)}", asdict(metrics)
            else:
                return True, "System resources normal", asdict(metrics)
                
        except Exception as e:
            return False, f"Error checking system resources: {str(e)}", {}
    
    def check_log_health(self) -> tuple:
        """Check logging system health."""
        try:
            from app.utils.enhanced_logging import get_log_health_stats
            
            stats = get_log_health_stats()
            if 'error' in stats:
                return False, "Log health monitoring not available", stats
            
            error_count = stats.get('error_count', 0)
            warning_count = stats.get('warning_count', 0)
            last_error_time = stats.get('last_error_time')
            
            # Check for recent errors
            if last_error_time:
                last_error = datetime.fromisoformat(last_error_time)
                time_since_error = datetime.now() - last_error
                
                if time_since_error < timedelta(minutes=5):
                    return False, f"Recent errors detected: {error_count} errors, {warning_count} warnings", stats
                elif time_since_error < timedelta(minutes=15):
                    return True, f"Some recent issues: {error_count} errors, {warning_count} warnings", stats
            
            return True, f"Logging healthy: {error_count} errors, {warning_count} warnings", stats
            
        except Exception as e:
            return False, f"Error checking log health: {str(e)}", {}
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}
        
        # Built-in checks
        builtin_checks = {
            'database': self.check_database_health,
            'system_resources': self.check_system_resources,
            'external_services': self.check_external_services,
            'log_health': self.check_log_health,
        }
        
        # Combine with custom checks
        all_checks = {**builtin_checks, **{name: info['func'] for name, info in self.checks.items()}}
        
        for check_name, check_func in all_checks.items():
            try:
                start_time = time.time()
                is_healthy, message, details = check_func()
                duration_ms = (time.time() - start_time) * 1000
                
                status = "healthy" if is_healthy else "unhealthy"
                
                result = HealthCheck(
                    name=check_name,
                    status=status,
                    message=message,
                    timestamp=datetime.utcnow().isoformat(),
                    duration_ms=duration_ms,
                    details=details or {}
                )
                
                results[check_name] = result
                
                # Update last result for custom checks
                if check_name in self.checks:
                    self.checks[check_name]['last_result'] = result
                
                logger.debug(f"Health check '{check_name}': {status} ({duration_ms:.2f}ms)")
                
            except Exception as e:
                logger.error(f"Health check '{check_name}' failed: {e}")
                results[check_name] = HealthCheck(
                    name=check_name,
                    status="unhealthy",
                    message=f"Check failed: {str(e)}",
                    timestamp=datetime.utcnow().isoformat(),
                    duration_ms=0,
                    details={'error': str(e)}
                )
        
        with self._lock:
            self.last_check_time = datetime.utcnow()
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a comprehensive health summary."""
        check_results = self.run_all_checks()
        metrics = self.get_system_metrics()
        
        # Calculate overall health
        healthy_checks = sum(1 for result in check_results.values() if result.status == "healthy")
        total_checks = len(check_results)
        overall_healthy = healthy_checks == total_checks
        
        # Store metrics in history
        with self._lock:
            self.metrics_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': asdict(metrics)
            })
            
            # Limit history size
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': metrics.uptime_seconds,
            'checks': {name: asdict(result) for name, result in check_results.items()},
            'metrics': asdict(metrics),
            'summary': {
                'total_checks': total_checks,
                'healthy_checks': healthy_checks,
                'unhealthy_checks': total_checks - healthy_checks
            }
        }
    
    def get_metrics_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical metrics data."""
        with self._lock:
            return self.metrics_history[-limit:]
    
    def save_health_report(self, filepath: Optional[Path] = None):
        """Save a detailed health report to file."""
        if filepath is None:
            filepath = Path("logs/health_report.json")
        
        filepath.parent.mkdir(exist_ok=True)
        
        report = {
            'report_time': datetime.utcnow().isoformat(),
            'health_summary': self.get_health_summary(),
            'metrics_history': self.get_metrics_history(),
            'thresholds': self.thresholds,
            'registered_checks': {
                name: {
                    'description': info['description'],
                    'last_result': asdict(info['last_result']) if info['last_result'] else None
                }
                for name, info in self.checks.items()
            }
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Health report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save health report: {e}")

# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None

def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor

def register_health_check(name: str, check_func: Callable[[], tuple], description: str = ""):
    """Register a custom health check with the global monitor."""
    monitor = get_health_monitor()
    monitor.register_check(name, check_func, description)

def get_health_status() -> Dict[str, Any]:
    """Get current health status."""
    monitor = get_health_monitor()
    return monitor.get_health_summary()

if __name__ == "__main__":
    # Test the health monitor
    logging.basicConfig(level=logging.DEBUG)
    
    monitor = HealthMonitor()
    
    # Register a custom check
    def custom_check():
        return True, "Custom check passed", {'test': 'data'}
    
    monitor.register_check("custom_test", custom_check, "Test custom check")
    
    # Run health checks
    print("Running health checks...")
    summary = monitor.get_health_summary()
    print(json.dumps(summary, indent=2, default=str))
    
    # Save report
    monitor.save_health_report()
    print("Health report saved")
