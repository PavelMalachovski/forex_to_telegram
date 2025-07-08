import os
import sys
import time
import logging
import threading
from pathlib import Path
from flask import Flask, jsonify

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def setup_enhanced_logging():
    """Setup enhanced logging with detailed formatting."""
    # Use environment variable or relative path
    log_dir = Path(os.getenv('LOG_DIR', project_root / 'logs'))
    log_dir.mkdir(exist_ok=True)
    
    # Create formatter with more details
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_dir / 'enhanced_app.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger

def create_flask_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Global variables for status tracking
    app_status = {
        'status': 'running',
        'start_time': time.time(),
        'heartbeat_count': 0,
        'last_heartbeat': None
    }
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for Render."""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'uptime': time.time() - app_status['start_time']
        }), 200
    
    @app.route('/status')
    def status():
        """Application status endpoint."""
        return jsonify({
            'status': app_status['status'],
            'start_time': app_status['start_time'],
            'uptime': time.time() - app_status['start_time'],
            'heartbeat_count': app_status['heartbeat_count'],
            'last_heartbeat': app_status['last_heartbeat'],
            'project_root': str(project_root)
        }), 200
    
    @app.route('/trigger-load')
    def trigger_load():
        """Endpoint for make.com to trigger data loading."""
        try:
            # Here you can add logic to trigger data loading
            return jsonify({
                'status': 'success',
                'message': 'Data loading triggered',
                'timestamp': time.time()
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }), 500
    
    @app.route('/trigger-today')
    def trigger_today():
        """Endpoint for make.com to trigger today's processing."""
        try:
            # Here you can add logic to trigger today's processing
            return jsonify({
                'status': 'success',
                'message': 'Today processing triggered',
                'timestamp': time.time()
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }), 500
    
    return app, app_status

def run_flask_server(app, port, logger):
    """Run Flask server in a separate thread."""
    try:
        logger.info(f"Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}", exc_info=True)

def main():
    """Production scheduler main function with HTTP server."""
    # Setup logging first
    logger = setup_enhanced_logging()
    logger.info("=== Production Scheduler Starting with HTTP Server ===")
    
    try:
        # Get port from environment or use default
        port = int(os.getenv('PORT', 8000))
        logger.info(f"Using port: {port}")
        
        # Test that paths work correctly
        logger.info(f"Project root: {project_root}")
        logger.info(f"Log directory: {Path(os.getenv('LOG_DIR', project_root / 'logs'))}")
        
        # Test importing existing modules
        try:
            from app.config import Config
            logger.info("✅ Successfully imported Config")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import Config: {e}")
        
        try:
            from app.services.notification_service import NotificationService
            logger.info("✅ Successfully imported NotificationService")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import NotificationService: {e}")
        
        try:
            from app.database.connection import DatabaseConnection
            logger.info("✅ Successfully imported DatabaseConnection")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import DatabaseConnection: {e}")
        
        # Create Flask app
        app, app_status = create_flask_app()
        
        # Start Flask server in a separate thread
        flask_thread = threading.Thread(
            target=run_flask_server,
            args=(app, port, logger),
            daemon=True
        )
        flask_thread.start()
        logger.info(f"✅ Flask server started on port {port}")
        
        logger.info("=== Production scheduler with HTTP server started successfully ===")
        
        # Keep running with heartbeat
        logger.info("Application is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
                app_status['heartbeat_count'] += 1
                app_status['last_heartbeat'] = time.time()
                logger.info(f"Application heartbeat #{app_status['heartbeat_count']} - still running...")
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        
        return 0
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
