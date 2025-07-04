
"""
Enhanced signal handling for graceful shutdown with state preservation.
"""

import signal
import sys
import threading
import time
import logging
import json
import os
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class GracefulShutdownHandler:
    """
    Enhanced signal handler for graceful application shutdown.
    Supports state preservation, cleanup callbacks, and timeout management.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.shutdown_event = threading.Event()
        self.cleanup_callbacks = []
        self.state_file = Path("logs/app_state.json")
        self.shutdown_start_time = None
        self.original_handlers = {}
        self.is_shutting_down = False
        self._lock = threading.Lock()
        
        # Ensure state directory exists
        self.state_file.parent.mkdir(exist_ok=True)
        
        logger.info(f"GracefulShutdownHandler initialized with {timeout}s timeout")
    
    def register_cleanup_callback(self, callback: Callable, name: str = None):
        """Register a cleanup callback to be called during shutdown."""
        callback_info = {
            'callback': callback,
            'name': name or callback.__name__,
            'registered_at': datetime.now().isoformat()
        }
        self.cleanup_callbacks.append(callback_info)
        logger.debug(f"Registered cleanup callback: {callback_info['name']}")
    
    def save_application_state(self, state_data: Dict[str, Any]):
        """Save application state to file for recovery."""
        try:
            state_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'shutdown_reason': 'graceful',
                'state_data': state_data
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_info, f, indent=2, default=str)
            
            logger.info(f"Application state saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save application state: {e}")
    
    def load_application_state(self) -> Optional[Dict[str, Any]]:
        """Load previously saved application state."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state_info = json.load(f)
                
                logger.info(f"Loaded application state from {state_info['timestamp']}")
                return state_info.get('state_data')
        except Exception as e:
            logger.error(f"Failed to load application state: {e}")
        
        return None
    
    def _signal_handler(self, signum: int, frame):
        """Internal signal handler."""
        signal_name = signal.Signals(signum).name
        
        with self._lock:
            if self.is_shutting_down:
                logger.warning(f"Received {signal_name} during shutdown - forcing exit")
                self._force_exit()
                return
            
            self.is_shutting_down = True
            self.shutdown_start_time = time.time()
        
        logger.info(f"Received signal {signum} ({signal_name}) - initiating graceful shutdown")
        
        # Start shutdown in a separate thread to avoid blocking signal handler
        shutdown_thread = threading.Thread(
            target=self._perform_shutdown,
            args=(signum, signal_name),
            name="GracefulShutdown"
        )
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        # Set the shutdown event
        self.shutdown_event.set()
    
    def _perform_shutdown(self, signum: int, signal_name: str):
        """Perform the actual shutdown process."""
        try:
            logger.info("Starting graceful shutdown process")
            
            # Execute cleanup callbacks in reverse order (LIFO)
            for callback_info in reversed(self.cleanup_callbacks):
                try:
                    callback_name = callback_info['name']
                    callback_func = callback_info['callback']
                    
                    logger.info(f"Executing cleanup callback: {callback_name}")
                    start_time = time.time()
                    
                    callback_func()
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Cleanup callback '{callback_name}' completed in {elapsed:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Error in cleanup callback '{callback_info['name']}': {e}")
                    continue
                
                # Check if we're running out of time
                if self.shutdown_start_time and (time.time() - self.shutdown_start_time) > self.timeout:
                    logger.warning("Shutdown timeout reached - skipping remaining callbacks")
                    break
            
            # Save final state
            final_state = {
                'shutdown_signal': signum,
                'shutdown_signal_name': signal_name,
                'shutdown_time': datetime.utcnow().isoformat(),
                'callbacks_executed': len(self.cleanup_callbacks)
            }
            self.save_application_state(final_state)
            
            logger.info("Graceful shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
        finally:
            self._exit_application()
    
    def _force_exit(self):
        """Force immediate exit."""
        logger.critical("Forcing immediate exit")
        os._exit(1)
    
    def _exit_application(self):
        """Exit the application cleanly."""
        logger.info("Application exiting")
        sys.exit(0)
    
    def register_signals(self):
        """Register signal handlers for graceful shutdown."""
        signals_to_handle = [signal.SIGTERM, signal.SIGINT]
        
        for sig in signals_to_handle:
            try:
                self.original_handlers[sig] = signal.signal(sig, self._signal_handler)
                logger.debug(f"Registered handler for {signal.Signals(sig).name}")
            except (OSError, ValueError) as e:
                logger.warning(f"Could not register handler for {signal.Signals(sig).name}: {e}")
    
    def unregister_signals(self):
        """Restore original signal handlers."""
        for sig, original_handler in self.original_handlers.items():
            try:
                signal.signal(sig, original_handler)
                logger.debug(f"Restored original handler for {signal.Signals(sig).name}")
            except (OSError, ValueError) as e:
                logger.warning(f"Could not restore handler for {signal.Signals(sig).name}: {e}")
    
    def wait_for_shutdown(self, check_interval: float = 0.1):
        """Wait for shutdown signal. Returns True if shutdown was requested."""
        return self.shutdown_event.wait(check_interval)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_event.is_set()

class DelayedSignalHandler:
    """
    Context manager that delays signal handling for critical sections.
    Based on the "holy grail" pattern for protecting initialization/finalization.
    """
    
    SIGNAL_TRANSLATION_MAP = {
        signal.SIGINT: 'SIGINT',
        signal.SIGTERM: 'SIGTERM',
    }
    
    def __init__(self):
        self._sig = None
        self._frame = None
        self._old_signal_handler_map = None
        logger.debug("DelayedSignalHandler created")
    
    def __enter__(self):
        logger.debug("Entering protected block - delaying signal handling")
        self._old_signal_handler_map = {
            sig: signal.signal(sig, self._delayed_handler)
            for sig in self.SIGNAL_TRANSLATION_MAP.keys()
        }
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exiting protected block - restoring signal handlers")
        
        # Restore original handlers
        for sig, handler in self._old_signal_handler_map.items():
            signal.signal(sig, handler)
        
        # If a signal was received during the protected block, handle it now
        if self._sig is not None:
            signal_name = self.SIGNAL_TRANSLATION_MAP[self._sig]
            logger.warning(f"{signal_name} received during protected block - processing now")
            
            # Call the original handler
            original_handler = self._old_signal_handler_map[self._sig]
            if callable(original_handler):
                original_handler(self._sig, self._frame)
            elif original_handler == signal.SIG_DFL:
                # Default handler - re-raise the signal
                signal.signal(self._sig, signal.SIG_DFL)
                os.kill(os.getpid(), self._sig)
    
    def _delayed_handler(self, sig, frame):
        """Handler that delays signal processing."""
        signal_name = self.SIGNAL_TRANSLATION_MAP.get(sig, f"Signal-{sig}")
        logger.warning(f"{signal_name} received - delaying until protected block exits")
        
        self._sig = sig
        self._frame = frame

# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdownHandler] = None

def get_shutdown_handler(timeout: int = 30) -> GracefulShutdownHandler:
    """Get or create the global shutdown handler."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(timeout)
    return _shutdown_handler

def setup_signal_handling(timeout: int = 30):
    """Setup signal handling for the application."""
    handler = get_shutdown_handler(timeout)
    handler.register_signals()
    return handler

def register_cleanup_callback(callback: Callable, name: str = None):
    """Register a cleanup callback with the global shutdown handler."""
    handler = get_shutdown_handler()
    handler.register_cleanup_callback(callback, name)

def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    if _shutdown_handler:
        return _shutdown_handler.is_shutdown_requested()
    return False

def wait_for_shutdown(check_interval: float = 0.1) -> bool:
    """Wait for shutdown signal."""
    if _shutdown_handler:
        return _shutdown_handler.wait_for_shutdown(check_interval)
    return False

def protect_critical_section():
    """Create a context manager that protects critical sections from signals."""
    return DelayedSignalHandler()

if __name__ == "__main__":
    # Test the signal handler
    import time
    
    logging.basicConfig(level=logging.DEBUG)
    
    def test_cleanup():
        print("Cleanup function called")
        time.sleep(1)
        print("Cleanup completed")
    
    # Setup signal handling
    handler = setup_signal_handling(timeout=10)
    register_cleanup_callback(test_cleanup, "test_cleanup")
    
    print("Signal handler test - press Ctrl+C to test graceful shutdown")
    
    try:
        while not is_shutdown_requested():
            print("Working...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught in main loop")
    
    print("Main loop exited")
