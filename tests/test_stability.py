#!/usr/bin/env python3
"""
Test script to demonstrate enhanced stability features.
"""

import sys
import os
import time
import threading

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.enhanced_logging import setup_enhanced_logging, log_event, log_with_context
from app.utils.signal_handler import (
    setup_signal_handling, register_cleanup_callback, 
    is_shutdown_requested, protect_critical_section
)
from app.utils.health_monitor import get_health_monitor, register_health_check

def test_cleanup():
    """Test cleanup function."""
    print("🧹 Cleanup function called")
    time.sleep(1)
    print("✅ Cleanup completed")

def custom_health_check():
    """Custom health check for testing."""
    return True, "Test check passed", {"test_data": "ok"}

def simulate_work():
    """Simulate some work being done."""
    counter = 0
    while not is_shutdown_requested():
        counter += 1
        print(f"🔄 Working... iteration {counter}")
        
        # Log some events
        if counter % 5 == 0:
            logger.warning(f"Warning message at iteration {counter}")
        if counter % 10 == 0:
            log_event(logger, "work_milestone", f"Reached iteration {counter}", 
                     iteration=counter, timestamp=time.time())
        
        time.sleep(2)
    
    print("🛑 Work loop stopped due to shutdown request")

def main():
    """Main test function."""
    global logger
    
    print("🚀 Starting stability test...")
    
    # Setup enhanced logging
    logger = setup_enhanced_logging()
    logger.info("Test application started")
    
    # Setup signal handling
    setup_signal_handling(timeout=10)
    register_cleanup_callback(test_cleanup, "test_cleanup")
    
    # Setup health monitoring
    health_monitor = get_health_monitor()
    register_health_check("test_check", custom_health_check, "Test health check")
    
    print("✅ All systems initialized")
    
    # Test protected critical section
    print("🔒 Testing protected critical section...")
    with protect_critical_section():
        print("   Initializing critical resources...")
        time.sleep(3)
        print("   Critical initialization complete")
    
    # Log with context
    with log_with_context(logger, user_id="test_user", session_id="test_session"):
        logger.info("This message has context")
    
    # Start work simulation in a thread
    work_thread = threading.Thread(target=simulate_work, daemon=True)
    work_thread.start()
    
    print("📊 Health check results:")
    health_summary = health_monitor.get_health_summary()
    print(f"   Overall status: {health_summary['overall_status']}")
    print(f"   Total checks: {health_summary['summary']['total_checks']}")
    print(f"   Healthy checks: {health_summary['summary']['healthy_checks']}")
    
    print("\n🎯 Test running! Press Ctrl+C to test graceful shutdown...")
    print("   The application will:")
    print("   - Handle the signal gracefully")
    print("   - Run cleanup callbacks")
    print("   - Save application state")
    print("   - Exit cleanly")
    
    # Main loop
    try:
        while not is_shutdown_requested():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚡ KeyboardInterrupt caught in main loop")
    
    print("🏁 Test completed")

if __name__ == "__main__":
    main()
