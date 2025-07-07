
#!/usr/bin/env python3
"""
Standalone resource monitoring script for Render.com diagnostics.
Can be run independently or alongside the main application.
"""

import os
import sys
import time
import psutil
import json
import signal
from datetime import datetime

class ResourceMonitor:
    def __init__(self, interval=10, log_file=None):
        self.interval = interval
        self.log_file = log_file
        self.running = True
        self.start_time = time.time()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n[{datetime.utcnow().isoformat()}] Received signal {signum}, shutting down monitor...")
        self.running = False
    
    def log_message(self, message):
        """Log message to file and stdout."""
        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] {message}"
        
        print(log_line)
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(log_line + '\n')
                    f.flush()
            except Exception as e:
                print(f"Failed to write to log file: {e}")
    
    def get_system_metrics(self):
        """Get comprehensive system metrics."""
        try:
            # System metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                network_stats = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv,
                }
            except:
                network_stats = None
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'system': {
                    'cpu_percent': cpu_percent,
                    'cpu_count': psutil.cpu_count(),
                    'memory_total_gb': memory.total / 1024 / 1024 / 1024,
                    'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                    'memory_used_gb': memory.used / 1024 / 1024 / 1024,
                    'memory_percent': memory.percent,
                    'disk_total_gb': disk.total / 1024 / 1024 / 1024,
                    'disk_used_gb': disk.used / 1024 / 1024 / 1024,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                    'disk_percent': disk.percent,
                },
                'process': {
                    'pid': process.pid,
                    'memory_rss_mb': process_memory.rss / 1024 / 1024,
                    'memory_vms_mb': process_memory.vms / 1024 / 1024,
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'status': process.status(),
                },
                'environment': {
                    'render_hostname': os.getenv('RENDER_EXTERNAL_HOSTNAME'),
                    'render_service': os.getenv('RENDER_SERVICE_NAME'),
                    'render_service_id': os.getenv('RENDER_SERVICE_ID'),
                    'port': os.getenv('PORT', '10000'),
                    'python_version': sys.version.split()[0],
                },
                'network': network_stats,
            }
            
            return metrics
            
        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
    
    def check_alerts(self, metrics):
        """Check for alert conditions."""
        alerts = []
        
        if 'system' in metrics:
            system = metrics['system']
            
            # Memory alerts
            if system['memory_percent'] > 90:
                alerts.append(f"🚨 CRITICAL: System memory usage {system['memory_percent']:.1f}%")
            elif system['memory_percent'] > 80:
                alerts.append(f"⚠️ WARNING: System memory usage {system['memory_percent']:.1f}%")
            
            # CPU alerts
            if system['cpu_percent'] > 95:
                alerts.append(f"🚨 CRITICAL: CPU usage {system['cpu_percent']:.1f}%")
            elif system['cpu_percent'] > 80:
                alerts.append(f"⚠️ WARNING: CPU usage {system['cpu_percent']:.1f}%")
            
            # Disk alerts
            if system['disk_percent'] > 90:
                alerts.append(f"🚨 CRITICAL: Disk usage {system['disk_percent']:.1f}%")
            elif system['disk_percent'] > 80:
                alerts.append(f"⚠️ WARNING: Disk usage {system['disk_percent']:.1f}%")
        
        if 'process' in metrics:
            process = metrics['process']
            
            # Process memory alerts (for 512MB limit on free tier)
            if process['memory_rss_mb'] > 480:
                alerts.append(f"🚨 CRITICAL: Process memory {process['memory_rss_mb']:.1f}MB (close to 512MB limit)")
            elif process['memory_rss_mb'] > 400:
                alerts.append(f"⚠️ WARNING: Process memory {process['memory_rss_mb']:.1f}MB")
        
        return alerts
    
    def run(self):
        """Main monitoring loop."""
        self.log_message("🔍 Resource Monitor Started")
        self.log_message(f"Monitoring interval: {self.interval} seconds")
        self.log_message(f"PID: {os.getpid()}")
        
        if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
            self.log_message(f"Running on Render: {os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
        
        try:
            while self.running:
                # Get metrics
                metrics = self.get_system_metrics()
                
                # Check for alerts
                alerts = self.check_alerts(metrics)
                
                # Log alerts
                for alert in alerts:
                    self.log_message(alert)
                
                # Log summary every 10 intervals (or if there are alerts)
                if (time.time() - self.start_time) % (self.interval * 10) < self.interval or alerts:
                    if 'system' in metrics and 'process' in metrics:
                        summary = (
                            f"📊 METRICS: "
                            f"CPU: {metrics['system']['cpu_percent']:.1f}%, "
                            f"Mem: {metrics['system']['memory_percent']:.1f}% "
                            f"({metrics['system']['memory_available_gb']:.1f}GB free), "
                            f"Process: {metrics['process']['memory_rss_mb']:.1f}MB, "
                            f"Uptime: {metrics['uptime_seconds']/60:.1f}min"
                        )
                        self.log_message(summary)
                
                # Log full metrics to file if specified
                if self.log_file and 'error' not in metrics:
                    try:
                        metrics_file = self.log_file.replace('.log', '_metrics.jsonl')
                        with open(metrics_file, 'a') as f:
                            f.write(json.dumps(metrics) + '\n')
                    except Exception as e:
                        self.log_message(f"Failed to write metrics: {e}")
                
                time.sleep(self.interval)
                
        except Exception as e:
            self.log_message(f"❌ Monitor error: {e}")
        
        self.log_message("🔍 Resource Monitor Stopped")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Resource Monitor for Render.com')
    parser.add_argument('--interval', type=int, default=10, help='Monitoring interval in seconds')
    parser.add_argument('--log-file', type=str, help='Log file path')
    parser.add_argument('--duration', type=int, help='Run for specified duration in seconds')
    
    args = parser.parse_args()
    
    # Create log directory if needed
    if args.log_file:
        log_dir = os.path.dirname(args.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    
    monitor = ResourceMonitor(interval=args.interval, log_file=args.log_file)
    
    if args.duration:
        # Run for specified duration
        import threading
        def stop_monitor():
            time.sleep(args.duration)
            monitor.running = False
        
        timer = threading.Thread(target=stop_monitor, daemon=True)
        timer.start()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitor interrupted by user")

if __name__ == "__main__":
    main()
