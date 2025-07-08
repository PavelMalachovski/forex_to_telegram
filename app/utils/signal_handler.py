
"""Signal handling utilities for graceful shutdown."""

import signal
import sys
import time
import threading
from typing import Callable, Dict, List, Optional, Any
from loguru import logger


# Global state
cleanup_callbacks: List[Dict[str, Any]] = []
health_checks: Dict[str, Dict[str, Any]] = {}
original_handlers: Dict[int, Any] = {}
shutdown_event = threading.Event()
shutdown_timeout: Optional[float] = None


def register_cleanup_callback(
    callback: Callable[[], None],
    name: Optional[str] = None,
    priority: int = 0
) -> None:
    """
    Register a cleanup callback to be called during shutdown.
    
    Args:
        callback: Function to call during cleanup
        name: Optional name for the callback
        priority: Priority (higher numbers run first)
    """
    cleanup_callbacks.append({
        'callback': callback,
        'name': name or callback.__name__,
        'priority': priority
    })
    
    # Sort by priority (descending)
    cleanup_callbacks.sort(key=lambda x: x['priority'], reverse=True)
    
    logger.debug(f"Registered cleanup callback: {name or callback.__name__}")


def register_health_check(
    name: str,
    check_func: Callable[[], bool],
    description: str = "",
    timeout: float = 5.0
) -> None:
    """
    Register a health check function.
    
    Args:
        name: Name of the health check
        check_func: Function that returns True if healthy
        description: Description of what this check does
        timeout: Timeout for the check in seconds
    """
    health_checks[name] = {
        'func': check_func,
        'description': description,
        'timeout': timeout
    }
    
    logger.debug(f"Registered health check: {name}")


def signal_handler(signum: int, frame: Any) -> None:
    """
    Handle shutdown signals.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name} ({signum}), initiating graceful shutdown...")
    
    # Set shutdown event
    shutdown_event.set()
    
    # Run cleanup callbacks
    logger.info("Running cleanup callbacks...")
    for callback_info in cleanup_callbacks:
        try:
            callback_name = callback_info['name']
            callback_func = callback_info['callback']
            
            logger.debug(f"Running cleanup callback: {callback_name}")
            
            if shutdown_timeout is not None:
                # Run with timeout
                thread = threading.Thread(target=callback_func)
                thread.daemon = True
                thread.start()
                thread.join(timeout=shutdown_timeout)
                
                if thread.is_alive():
                    logger.warning(f"Cleanup callback {callback_name} timed out")
                else:
                    logger.debug(f"Cleanup callback {callback_name} completed")
            else:
                # Run without timeout
                callback_func()
                logger.debug(f"Cleanup callback {callback_name} completed")
                
        except Exception as e:
            logger.error(f"Error in cleanup callback {callback_info['name']}: {e}")
    
    logger.info("Graceful shutdown completed")
    
    # Restore original handler and re-raise signal
    if signum in original_handlers:
        signal.signal(signum, original_handlers[signum])
        signal.raise_signal(signum)
    else:
        sys.exit(0)


def setup_signal_handling(timeout: Optional[float] = None) -> Callable[[int, Any], None]:
    """
    Setup signal handling for graceful shutdown.
    
    Args:
        timeout: Timeout for cleanup callbacks in seconds
        
    Returns:
        The signal handler function
    """
    global shutdown_timeout
    shutdown_timeout = timeout
    
    # Store original handlers
    for sig in [signal.SIGTERM, signal.SIGINT]:
        try:
            original_handlers[sig] = signal.signal(sig, signal_handler)
            logger.debug(f"Registered signal handler for {signal.Signals(sig).name}")
        except (OSError, ValueError) as e:
            logger.warning(f"Could not register handler for signal {sig}: {e}")
    
    logger.info("Signal handling setup completed")
    return signal_handler


def is_shutdown_requested() -> bool:
    """
    Check if shutdown has been requested.
    
    Returns:
        True if shutdown was requested
    """
    return shutdown_event.is_set()


def wait_for_shutdown(check_interval: float = 1.0) -> None:
    """
    Wait for shutdown signal.
    
    Args:
        check_interval: How often to check for shutdown in seconds
    """
    logger.info("Waiting for shutdown signal...")
    
    try:
        while not shutdown_event.is_set():
            time.sleep(check_interval)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_event.set()


def run_health_checks() -> Dict[str, Any]:
    """
    Run all registered health checks.
    
    Returns:
        Dictionary with health check results
    """
    results = {
        'healthy': True,
        'checks': {},
        'timestamp': time.time()
    }
    
    for name, check_info in health_checks.items():
        try:
            check_func = check_info['func']
            timeout = check_info['timeout']
            
            # Run health check with timeout
            result = {'healthy': False, 'error': None, 'duration': 0}
            start_time = time.time()
            
            if timeout > 0:
                # Run with timeout using threading
                check_result = [False]
                error_result = [None]
                
                def run_check():
                    try:
                        check_result[0] = check_func()
                    except Exception as e:
                        error_result[0] = str(e)
                
                thread = threading.Thread(target=run_check)
                thread.daemon = True
                thread.start()
                thread.join(timeout=timeout)
                
                if thread.is_alive():
                    result['error'] = f"Health check timed out after {timeout}s"
                elif error_result[0]:
                    result['error'] = error_result[0]
                else:
                    result['healthy'] = check_result[0]
            else:
                # Run without timeout
                try:
                    result['healthy'] = check_func()
                except Exception as e:
                    result['error'] = str(e)
            
            result['duration'] = time.time() - start_time
            results['checks'][name] = result
            
            if not result['healthy']:
                results['healthy'] = False
                
        except Exception as e:
            results['checks'][name] = {
                'healthy': False,
                'error': f"Failed to run health check: {e}",
                'duration': 0
            }
            results['healthy'] = False
    
    return results


def cleanup_signal_handlers() -> None:
    """Restore original signal handlers."""
    for sig, handler in original_handlers.items():
        try:
            signal.signal(sig, handler)
            logger.debug(f"Restored original handler for signal {sig}")
        except (OSError, ValueError) as e:
            logger.warning(f"Could not restore handler for signal {sig}: {e}")
    
    original_handlers.clear()
    logger.debug("Signal handlers cleanup completed")


# Health check functions
def basic_health_check() -> bool:
    """Basic health check that always returns True."""
    return True


def memory_health_check(max_memory_mb: float = 1000.0) -> bool:
    """
    Check if memory usage is within limits.
    
    Args:
        max_memory_mb: Maximum memory usage in MB
        
    Returns:
        True if memory usage is acceptable
    """
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        return memory_mb < max_memory_mb
    except ImportError:
        logger.warning("psutil not available for memory health check")
        return True
    except Exception as e:
        logger.error(f"Error in memory health check: {e}")
        return False


def disk_health_check(min_free_gb: float = 1.0) -> bool:
    """
    Check if disk space is sufficient.
    
    Args:
        min_free_gb: Minimum free disk space in GB
        
    Returns:
        True if disk space is sufficient
    """
    try:
        import psutil
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / 1024 / 1024 / 1024
        return free_gb > min_free_gb
    except ImportError:
        logger.warning("psutil not available for disk health check")
        return True
    except Exception as e:
        logger.error(f"Error in disk health check: {e}")
        return False


# Register default health checks
def register_default_health_checks() -> None:
    """Register default health checks."""
    register_health_check(
        "basic",
        basic_health_check,
        "Basic health check"
    )
    
    register_health_check(
        "memory",
        lambda: memory_health_check(1000.0),
        "Memory usage check (max 1GB)"
    )
    
    register_health_check(
        "disk",
        lambda: disk_health_check(1.0),
        "Disk space check (min 1GB free)"
    )
