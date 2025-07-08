
#!/usr/bin/env python3
"""Resource monitoring script for the Forex Bot application."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ResourceMonitor:
    """Resource monitoring class."""
    
    def __init__(self, output_file: Optional[str] = None):
        """
        Initialize the resource monitor.
        
        Args:
            output_file: Optional output file for metrics
        """
        self.output_file = output_file
        self.start_time = time.time()
        self.metrics_history: List[Dict[str, Any]] = []
        
        # Try to import psutil
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            self.psutil = None
            self.psutil_available = False
            logger.warning("psutil not available - limited monitoring capabilities")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': time.time() - self.start_time,
        }
        
        if not self.psutil_available:
            metrics['error'] = 'psutil not available'
            return metrics
        
        try:
            # CPU metrics
            cpu_percent = self.psutil.cpu_percent(interval=1)
            cpu_count = self.psutil.cpu_count()
            
            metrics['cpu'] = {
                'percent': cpu_percent,
                'count': cpu_count,
                'load_average': list(self.psutil.getloadavg()) if hasattr(self.psutil, 'getloadavg') else None
            }
            
            # Memory metrics
            memory = self.psutil.virtual_memory()
            swap = self.psutil.swap_memory()
            
            metrics['memory'] = {
                'total_gb': memory.total / 1024 / 1024 / 1024,
                'available_gb': memory.available / 1024 / 1024 / 1024,
                'used_gb': memory.used / 1024 / 1024 / 1024,
                'percent': memory.percent,
                'swap_total_gb': swap.total / 1024 / 1024 / 1024,
                'swap_used_gb': swap.used / 1024 / 1024 / 1024,
                'swap_percent': swap.percent
            }
            
            # Disk metrics
            disk_usage = self.psutil.disk_usage('/')
            
            metrics['disk'] = {
                'total_gb': disk_usage.total / 1024 / 1024 / 1024,
                'used_gb': disk_usage.used / 1024 / 1024 / 1024,
                'free_gb': disk_usage.free / 1024 / 1024 / 1024,
                'percent': (disk_usage.used / disk_usage.total) * 100
            }
            
            # Network metrics (if available)
            try:
                network = self.psutil.net_io_counters()
                metrics['network'] = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv,
                }
            except Exception:
                metrics['network'] = None
            
            # Process metrics
            try:
                process = self.psutil.Process()
                process_memory = process.memory_info()
                
                metrics['process'] = {
                    'pid': process.pid,
                    'memory_rss_mb': process_memory.rss / 1024 / 1024,
                    'memory_vms_mb': process_memory.vms / 1024 / 1024,
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'create_time': process.create_time(),
                    'status': process.status()
                }
            except Exception as e:
                metrics['process'] = {'error': str(e)}
            
        except Exception as e:
            metrics['error'] = str(e)
            logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """
        Get application-specific metrics.
        
        Returns:
            Dictionary with application metrics
        """
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        try:
            # Try to get database connection info
            from app.database.connection import get_db
            
            try:
                db = next(get_db())
                metrics['database'] = {
                    'connection_status': 'connected',
                    'connection_time': datetime.utcnow().isoformat()
                }
                
                # Get basic table counts
                from app.database.models import NewsEvent, BotUser, Currency, ImpactLevel
                
                metrics['database']['table_counts'] = {
                    'news_events': db.query(NewsEvent).count(),
                    'bot_users': db.query(BotUser).count(),
                    'currencies': db.query(Currency).count(),
                    'impact_levels': db.query(ImpactLevel).count()
                }
                
            except Exception as e:
                metrics['database'] = {
                    'connection_status': 'error',
                    'error': str(e)
                }
            
            # Check log files
            logs_dir = Path('logs')
            if logs_dir.exists():
                log_files = list(logs_dir.glob('*.log'))
                metrics['logs'] = {
                    'log_files_count': len(log_files),
                    'total_size_mb': sum(f.stat().st_size for f in log_files) / 1024 / 1024
                }
            
        except Exception as e:
            metrics['error'] = str(e)
            logger.error(f"Error collecting application metrics: {e}")
        
        return metrics
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect all metrics.
        
        Returns:
            Dictionary with all metrics
        """
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': self.get_system_metrics(),
            'application': self.get_application_metrics()
        }
        
        # Store in history
        self.metrics_history.append(metrics)
        
        # Keep only last 100 entries
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return metrics
    
    def save_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Save metrics to file.
        
        Args:
            metrics: Metrics dictionary to save
        """
        if not self.output_file:
            return
        
        try:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to JSONL file
            with open(output_path, 'a') as f:
                f.write(json.dumps(metrics) + '\n')
                
        except Exception as e:
            logger.error(f"Error saving metrics to {self.output_file}: {e}")
    
    def print_metrics(self, metrics: Dict[str, Any], detailed: bool = False) -> None:
        """
        Print metrics to console.
        
        Args:
            metrics: Metrics dictionary to print
            detailed: Whether to print detailed metrics
        """
        timestamp = metrics['timestamp']
        print(f"\n=== Resource Monitor - {timestamp} ===")
        
        # System metrics
        system = metrics.get('system', {})
        if 'error' in system:
            print(f"System: ERROR - {system['error']}")
        else:
            if 'cpu' in system:
                cpu = system['cpu']
                print(f"CPU: {cpu.get('percent', 0):.1f}% ({cpu.get('count', 0)} cores)")
            
            if 'memory' in system:
                memory = system['memory']
                print(f"Memory: {memory.get('percent', 0):.1f}% ({memory.get('used_gb', 0):.1f}GB / {memory.get('total_gb', 0):.1f}GB)")
            
            if 'disk' in system:
                disk = system['disk']
                print(f"Disk: {disk.get('percent', 0):.1f}% ({disk.get('used_gb', 0):.1f}GB / {disk.get('total_gb', 0):.1f}GB)")
            
            if 'process' in system and isinstance(system['process'], dict):
                process = system['process']
                if 'error' not in process:
                    print(f"Process: {process.get('memory_rss_mb', 0):.1f}MB RAM, {process.get('cpu_percent', 0):.1f}% CPU")
        
        # Application metrics
        app = metrics.get('application', {})
        if 'database' in app:
            db = app['database']
            status = db.get('connection_status', 'unknown')
            print(f"Database: {status}")
            
            if 'table_counts' in db and detailed:
                counts = db['table_counts']
                print(f"  - Events: {counts.get('news_events', 0)}")
                print(f"  - Users: {counts.get('bot_users', 0)}")
                print(f"  - Currencies: {counts.get('currencies', 0)}")
        
        if 'logs' in app and detailed:
            logs = app['logs']
            print(f"Logs: {logs.get('log_files_count', 0)} files, {logs.get('total_size_mb', 0):.1f}MB")
    
    def run_continuous_monitoring(
        self,
        interval: int = 60,
        duration: Optional[int] = None,
        detailed: bool = False
    ) -> None:
        """
        Run continuous monitoring.
        
        Args:
            interval: Monitoring interval in seconds
            duration: Total duration in seconds (None for infinite)
            detailed: Whether to print detailed metrics
        """
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Print metrics
                self.print_metrics(metrics, detailed=detailed)
                
                # Save metrics
                self.save_metrics(metrics)
                
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"Monitoring completed after {duration} seconds")
                    break
                
                # Wait for next iteration
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}")
    
    def get_summary_report(self) -> Dict[str, Any]:
        """
        Get summary report of collected metrics.
        
        Returns:
            Summary report dictionary
        """
        if not self.metrics_history:
            return {'error': 'No metrics collected'}
        
        # Calculate averages and trends
        cpu_values = []
        memory_values = []
        disk_values = []
        
        for metrics in self.metrics_history:
            system = metrics.get('system', {})
            
            if 'cpu' in system and 'percent' in system['cpu']:
                cpu_values.append(system['cpu']['percent'])
            
            if 'memory' in system and 'percent' in system['memory']:
                memory_values.append(system['memory']['percent'])
            
            if 'disk' in system and 'percent' in system['disk']:
                disk_values.append(system['disk']['percent'])
        
        summary = {
            'monitoring_duration': time.time() - self.start_time,
            'total_samples': len(self.metrics_history),
            'averages': {}
        }
        
        if cpu_values:
            summary['averages']['cpu_percent'] = sum(cpu_values) / len(cpu_values)
            summary['averages']['cpu_max'] = max(cpu_values)
            summary['averages']['cpu_min'] = min(cpu_values)
        
        if memory_values:
            summary['averages']['memory_percent'] = sum(memory_values) / len(memory_values)
            summary['averages']['memory_max'] = max(memory_values)
            summary['averages']['memory_min'] = min(memory_values)
        
        if disk_values:
            summary['averages']['disk_percent'] = sum(disk_values) / len(disk_values)
            summary['averages']['disk_max'] = max(disk_values)
            summary['averages']['disk_min'] = min(disk_values)
        
        return summary


def main() -> int:
    """
    Main function.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Monitor system and application resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --once
  %(prog)s --interval 30 --duration 3600
  %(prog)s --interval 60 --output metrics.jsonl --detailed
        """
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run monitoring once and exit'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Monitoring interval in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        help='Total monitoring duration in seconds (default: infinite)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for metrics (JSONL format)'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed metrics'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary report at the end'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize monitor
        monitor = ResourceMonitor(output_file=args.output)
        
        if args.once:
            # Single monitoring run
            metrics = monitor.collect_metrics()
            monitor.print_metrics(metrics, detailed=args.detailed)
            monitor.save_metrics(metrics)
        else:
            # Continuous monitoring
            monitor.run_continuous_monitoring(
                interval=args.interval,
                duration=args.duration,
                detailed=args.detailed
            )
            
            # Show summary if requested
            if args.summary:
                summary = monitor.get_summary_report()
                print("\n=== MONITORING SUMMARY ===")
                print(json.dumps(summary, indent=2))
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Monitoring cancelled by user")
        return 0
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
