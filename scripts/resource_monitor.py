
#!/usr/bin/env python3
"""
Resource monitoring script for the Forex Bot
Logs CPU, memory, and disk usage to help diagnose SIGTERM causes
"""

import psutil
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "resource_monitor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ResourceMonitor:
    def __init__(self, interval=30):
        self.interval = interval
        self.process_name = "enhanced_main.py"
        self.log_file = log_dir / "resource_usage.json"
        
    def get_process_info(self):
        """Get information about the main application process"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
            try:
                if self.process_name in ' '.join(proc.info['cmdline'] or []):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def get_system_resources(self):
        """Get system-wide resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_total_mb': memory.total // (1024 * 1024),
                'memory_used_mb': memory.used // (1024 * 1024),
                'memory_percent': memory.percent,
                'disk_total_gb': disk.total // (1024 * 1024 * 1024),
                'disk_used_gb': disk.used // (1024 * 1024 * 1024),
                'disk_percent': (disk.used / disk.total) * 100
            }
        }
    
    def get_process_resources(self, proc):
        """Get process-specific resource usage"""
        try:
            memory_info = proc.memory_info()
            cpu_percent = proc.cpu_percent()
            
            return {
                'pid': proc.pid,
                'memory_rss_mb': memory_info.rss // (1024 * 1024),
                'memory_vms_mb': memory_info.vms // (1024 * 1024),
                'cpu_percent': cpu_percent,
                'num_threads': proc.num_threads(),
                'status': proc.status()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def log_resources(self):
        """Log current resource usage"""
        data = self.get_system_resources()
        
        # Get process-specific info
        proc = self.get_process_info()
        if proc:
            data['process'] = self.get_process_resources(proc)
        else:
            data['process'] = None
            logger.warning(f"Process {self.process_name} not found")
        
        # Log to file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(data) + '\n')
        
        # Log summary to console
        if data['process']:
            logger.info(
                f"System: CPU {data['system']['cpu_percent']:.1f}%, "
                f"Memory {data['system']['memory_percent']:.1f}% | "
                f"Process: CPU {data['process']['cpu_percent']:.1f}%, "
                f"Memory {data['process']['memory_rss_mb']}MB"
            )
        else:
            logger.info(
                f"System: CPU {data['system']['cpu_percent']:.1f}%, "
                f"Memory {data['system']['memory_percent']:.1f}%"
            )
        
        # Check for high resource usage
        self.check_resource_alerts(data)
    
    def check_resource_alerts(self, data):
        """Check for resource usage that might lead to termination"""
        system = data['system']
        process = data.get('process')
        
        # System alerts
        if system['memory_percent'] > 90:
            logger.warning(f"HIGH SYSTEM MEMORY USAGE: {system['memory_percent']:.1f}%")
        
        if system['cpu_percent'] > 95:
            logger.warning(f"HIGH SYSTEM CPU USAGE: {system['cpu_percent']:.1f}%")
        
        # Process alerts
        if process:
            if process['memory_rss_mb'] > 400:  # Alert if process uses > 400MB
                logger.warning(f"HIGH PROCESS MEMORY USAGE: {process['memory_rss_mb']}MB")
            
            if process['cpu_percent'] > 80:
                logger.warning(f"HIGH PROCESS CPU USAGE: {process['cpu_percent']:.1f}%")
    
    def run(self):
        """Main monitoring loop"""
        logger.info(f"Starting resource monitor (interval: {self.interval}s)")
        
        try:
            while True:
                self.log_resources()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Resource monitor stopped by user")
        except Exception as e:
            logger.error(f"Resource monitor error: {e}")

if __name__ == "__main__":
    monitor = ResourceMonitor(interval=30)
    monitor.run()
