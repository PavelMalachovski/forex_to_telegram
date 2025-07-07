
"""
Enhanced main application with improved signal handling, health monitoring, and stability.
"""

import os
import sys
import time
import threading
import signal
import psutil
import traceback
import json
import gc
from datetime import datetime
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.timezone_utils import get_current_time_iso
from app.database.connection import init_database, SessionLocal
from app.bot.handlers import BotHandlers
from app.services.data_loader_service import DataLoaderService
from app.services.today_service import TodayService

import telebot
import logging
from flask import Flask, request, jsonify

# Global variables for monitoring
shutdown_requested = False
app_start_time = time.time()
resource_monitor_thread = None

# Setup enhanced logging
def setup_enhanced_logging():
    """Setup enhanced logging with detailed formatting."""
    log_dir = Path('/home/ubuntu/forex_bot_postgresql/logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create formatter with more details
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_dir / 'enhanced_app.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def log_system_state(logger, context=""):
    """Log detailed system state for diagnostics."""
    try:
        # Process info
        process = psutil.Process()
        process_info = {
            'pid': process.pid,
            'ppid': process.ppid(),
            'memory_rss_mb': process.memory_info().rss / 1024 / 1024,
            'memory_vms_mb': process.memory_info().vms / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'status': process.status(),
            'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
        }
        
        # System info
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_info = {
            'system_memory_total_gb': memory.total / 1024 / 1024 / 1024,
            'system_memory_available_gb': memory.available / 1024 / 1024 / 1024,
            'system_memory_percent': memory.percent,
            'system_cpu_percent': psutil.cpu_percent(interval=1),
            'system_cpu_count': psutil.cpu_count(),
            'disk_usage_percent': disk.percent,
            'disk_free_gb': disk.free / 1024 / 1024 / 1024,
        }
        
        # Python GC info
        gc_info = {
            'gc_counts': gc.get_count(),
            'gc_stats': gc.get_stats() if hasattr(gc, 'get_stats') else None,
        }
        
        # Environment info
        env_info = {
            'render_external_hostname': os.getenv('RENDER_EXTERNAL_HOSTNAME'),
            'render_service_id': os.getenv('RENDER_SERVICE_ID'),
            'render_service_name': os.getenv('RENDER_SERVICE_NAME'),
            'port': os.getenv('PORT', '10000'),
            'python_version': sys.version,
            'uptime_seconds': time.time() - app_start_time,
        }
        
        logger.info(f"=== SYSTEM STATE {context} ===")
        logger.info(f"Process Info: {json.dumps(process_info, indent=2)}")
        logger.info(f"System Info: {json.dumps(system_info, indent=2)}")
        logger.info(f"GC Info: {json.dumps(gc_info, indent=2)}")
        logger.info(f"Environment Info: {json.dumps(env_info, indent=2)}")
        logger.info("=== END SYSTEM STATE ===")
        
    except Exception as e:
        logger.error(f"Failed to log system state: {e}")

def resource_monitor_worker(logger):
    """Background worker to monitor resources continuously."""
    global shutdown_requested
    
    logger.info("Resource monitor started")
    
    while not shutdown_requested:
        try:
            # Log system state every 60 seconds
            log_system_state(logger, "PERIODIC_CHECK")
            
            # Check for memory pressure
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                logger.warning(f"HIGH MEMORY USAGE: {memory.percent:.1f}%")
            
            # Check for high CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                logger.warning(f"HIGH CPU USAGE: {cpu_percent:.1f}%")
            
            # Check process memory
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            if process_memory_mb > 400:  # Warn if using more than 400MB (close to 512MB limit)
                logger.warning(f"HIGH PROCESS MEMORY: {process_memory_mb:.1f}MB")
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Resource monitor error: {e}")
            time.sleep(30)  # Shorter sleep on error
    
    logger.info("Resource monitor stopped")

class EnhancedSignalHandler:
    """Enhanced signal handler with detailed logging and diagnostics."""
    
    def __init__(self, timeout=25):
        self.timeout = timeout
        self.shutdown_requested = False
        self.cleanup_callbacks = []
        self.logger = logging.getLogger(__name__)
        
    def setup(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGUSR1, self._debug_signal_handler)  # For debugging
        self.logger.info("Enhanced signal handlers registered (SIGTERM, SIGINT, SIGUSR1)")
        
    def _debug_signal_handler(self, signum, frame):
        """Handle debug signal to dump current state."""
        self.logger.info(f"DEBUG SIGNAL {signum} received - dumping state")
        log_system_state(self.logger, "DEBUG_SIGNAL")
        
    def _signal_handler(self, signum, frame):
        """Handle termination signals with comprehensive logging."""
        global shutdown_requested
        
        signal_name = signal.Signals(signum).name
        self.logger.critical(f"🚨 SIGNAL {signum} ({signal_name}) RECEIVED - INITIATING SHUTDOWN")
        
        # Log the exact time and context
        shutdown_time = datetime.utcnow().isoformat()
        uptime = time.time() - app_start_time
        
        self.logger.critical(f"Shutdown initiated at: {shutdown_time}")
        self.logger.critical(f"Application uptime: {uptime:.2f} seconds ({uptime/60:.2f} minutes)")
        
        # Log stack trace for debugging
        stack_trace = ''.join(traceback.format_stack(frame))
        self.logger.critical(f"Signal received at stack:\n{stack_trace}")
        
        # Log comprehensive system state
        log_system_state(self.logger, "SIGNAL_RECEIVED")
        
        # Check for common SIGTERM causes
        self._diagnose_sigterm_cause()
        
        shutdown_requested = True
        self.shutdown_requested = True
        self._cleanup()
        
    def _diagnose_sigterm_cause(self):
        """Attempt to diagnose the cause of SIGTERM."""
        self.logger.critical("=== SIGTERM DIAGNOSIS ===")
        
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory.percent > 90:
                self.logger.critical(f"❌ LIKELY CAUSE: System memory exhaustion ({memory.percent:.1f}%)")
            elif process_memory_mb > 480:  # Close to 512MB limit
                self.logger.critical(f"❌ LIKELY CAUSE: Process memory limit exceeded ({process_memory_mb:.1f}MB)")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 95:
                self.logger.critical(f"❌ LIKELY CAUSE: CPU exhaustion ({cpu_percent:.1f}%)")
            
            # Check uptime (for free tier timeout)
            uptime_minutes = (time.time() - app_start_time) / 60
            if uptime_minutes > 14 and uptime_minutes < 16:
                self.logger.critical(f"❌ LIKELY CAUSE: Free tier 15-minute timeout (uptime: {uptime_minutes:.1f} min)")
            
            # Check for Render-specific environment
            if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
                self.logger.critical("🔍 Running on Render.com - checking Render-specific causes")
                
                # Check if this might be a health check failure
                if uptime_minutes < 5:
                    self.logger.critical("❌ POSSIBLE CAUSE: Health check failure (early shutdown)")
                
                # Check if this might be a deployment
                if os.getenv('RENDER_GIT_COMMIT'):
                    self.logger.critical(f"🔍 Git commit: {os.getenv('RENDER_GIT_COMMIT')}")
            
            self.logger.critical("=== END DIAGNOSIS ===")
            
        except Exception as e:
            self.logger.error(f"Failed to diagnose SIGTERM cause: {e}")
        
    def _cleanup(self):
        """Execute cleanup callbacks."""
        self.logger.critical("🧹 Starting cleanup process")
        
        cleanup_start = time.time()
        
        for i, callback in enumerate(self.cleanup_callbacks):
            try:
                self.logger.info(f"Executing cleanup callback {i+1}/{len(self.cleanup_callbacks)}")
                callback()
            except Exception as e:
                self.logger.error(f"Cleanup callback {i+1} error: {e}")
        
        cleanup_duration = time.time() - cleanup_start
        self.logger.critical(f"✅ Cleanup completed in {cleanup_duration:.2f} seconds")
        
        # Final system state
        log_system_state(self.logger, "FINAL_STATE")
        
        # Force exit with proper code
        self.logger.critical("🔚 Exiting application")
        sys.exit(0)
        
    def register_cleanup(self, callback):
        """Register cleanup callback."""
        self.cleanup_callbacks.append(callback)

class EnhancedTelegramBotApplication:
    """
    Enhanced Telegram bot application with comprehensive error handling,
    health monitoring, and graceful shutdown capabilities.
    """
    
    def __init__(self):
        self.bot = None
        self.bot_handlers = None
        self.flask_app = None
        self.is_webhook_mode = self._is_webhook_mode()
        self.webhook_url = None
        self.shutdown_handler = None
        self.polling_thread = None
        self.flask_thread = None
        self.logger = None
        self.start_time = time.time()
        
        # Application state for recovery
        self.app_state = {
            'start_time': datetime.utcnow().isoformat(),
            'mode': 'webhook' if self.is_webhook_mode else 'polling',
            'initialization_complete': False,
            'services_started': False
        }
    
    def _is_webhook_mode(self):
        """Determine if we should use webhook mode."""
        return (
            os.getenv('RENDER_EXTERNAL_HOSTNAME') is not None or
            os.getenv('WEBHOOK_MODE', '').lower() == 'true'
        )
    
    def _get_webhook_url(self):
        """Get webhook URL for production."""
        if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
            return f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        elif os.getenv('WEBHOOK_URL'):
            return os.getenv('WEBHOOK_URL')
        else:
            return None
    
    def initialize(self):
        """Initialize the application with enhanced error handling."""
        global resource_monitor_thread
        
        self.logger = setup_enhanced_logging()
        self.logger.info("🚀 Starting Enhanced Telegram Bot Application")
        
        # Log initial system state
        log_system_state(self.logger, "STARTUP")
        
        # Setup signal handling
        self.shutdown_handler = EnhancedSignalHandler(timeout=30)
        self.shutdown_handler.setup()
        
        # Register cleanup callbacks
        self.shutdown_handler.register_cleanup(self._cleanup_telegram_bot)
        self.shutdown_handler.register_cleanup(self._cleanup_flask_app)
        self.shutdown_handler.register_cleanup(self._cleanup_database)
        
        # Start resource monitoring
        resource_monitor_thread = threading.Thread(
            target=resource_monitor_worker, 
            args=(self.logger,), 
            daemon=True
        )
        resource_monitor_thread.start()
        self.logger.info("Resource monitor thread started")
        
        self._validate_configuration()
        self._initialize_database()
        self._initialize_telegram_bot()
        self._initialize_flask_app()
        self._setup_webhook_if_needed()
        
        self.app_state['initialization_complete'] = True
        self.logger.info("✅ Application initialization completed successfully")
    
    def _validate_configuration(self):
        """Validate application configuration."""
        self.logger.info("🔍 Validating configuration...")
        
        if not config.validate():
            self.logger.error("❌ Configuration validation failed")
            raise SystemExit(1)
        
        self.logger.info("✅ Configuration validated successfully")
    
    def _initialize_database(self):
        """Initialize database connection."""
        self.logger.info("🗄️ Initializing database...")
        
        try:
            init_database()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise SystemExit(1)
    
    def _initialize_telegram_bot(self):
        """Initialize Telegram bot."""
        self.logger.info("🤖 Initializing Telegram bot...")
        
        if not config.TELEGRAM_BOT_TOKEN:
            self.logger.error("❌ TELEGRAM_BOT_TOKEN not configured")
            raise SystemExit(1)
        
        try:
            self.bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
            self.bot_handlers = BotHandlers(self.bot, lambda: SessionLocal())
            
            # Test bot token validity
            if not config.TELEGRAM_BOT_TOKEN.startswith('your_'):
                try:
                    bot_info = self.bot.get_me()
                    self.logger.info(f"✅ Bot token validated: @{bot_info.username}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Bot token validation failed: {e}")
                    if self.is_webhook_mode:
                        self.logger.error("❌ Invalid bot token in production mode")
                        raise SystemExit(1)
            else:
                self.logger.warning("⚠️ Using placeholder bot token")
            
            self.logger.info("✅ Telegram bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Telegram bot: {e}")
            raise SystemExit(1)
    
    def _initialize_flask_app(self):
        """Initialize Flask application with enhanced endpoints."""
        self.logger.info("🌐 Initializing Flask application...")
        
        self.flask_app = Flask(__name__)
        self._setup_flask_routes()
        
        self.logger.info("✅ Flask application initialized")
    
    def _setup_flask_routes(self):
        """Setup Flask routes with enhanced health and monitoring endpoints."""
        
        @self.flask_app.route('/health', methods=['GET'])
        @self.flask_app.route('/ping', methods=['GET'])
        def health_check():
            """Enhanced health check endpoint with detailed diagnostics."""
            try:
                # Basic health info
                uptime = time.time() - app_start_time
                
                # System metrics
                memory = psutil.virtual_memory()
                process = psutil.Process()
                process_memory_mb = process.memory_info().rss / 1024 / 1024
                
                health_data = {
                    'status': 'healthy',
                    'timestamp': get_current_time_iso(),
                    'uptime_seconds': uptime,
                    'uptime_minutes': uptime / 60,
                    'mode': self.app_state['mode'],
                    'system': {
                        'memory_percent': memory.percent,
                        'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                        'cpu_percent': psutil.cpu_percent(),
                        'process_memory_mb': process_memory_mb,
                        'process_threads': process.num_threads(),
                    },
                    'environment': {
                        'render_hostname': os.getenv('RENDER_EXTERNAL_HOSTNAME'),
                        'render_service': os.getenv('RENDER_SERVICE_NAME'),
                        'port': os.getenv('PORT', '10000'),
                    },
                    'application': {
                        'initialization_complete': self.app_state['initialization_complete'],
                        'services_started': self.app_state['services_started'],
                        'bot_available': self.bot is not None,
                        'webhook_url': self.webhook_url,
                    }
                }
                
                # Determine status based on health
                status_code = 200
                if memory.percent > 90 or process_memory_mb > 480:
                    health_data['status'] = 'warning'
                    health_data['warnings'] = ['high_memory_usage']
                    status_code = 200  # Still return 200 for health checks
                
                return jsonify(health_data), status_code
                
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
        
        @self.flask_app.route('/debug/state', methods=['GET'])
        def debug_state():
            """Debug endpoint to dump current application state."""
            try:
                # Trigger state logging
                log_system_state(self.logger, "DEBUG_ENDPOINT")
                
                return jsonify({
                    'message': 'State logged to application logs',
                    'timestamp': get_current_time_iso()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.flask_app.route('/debug/gc', methods=['POST'])
        def debug_gc():
            """Debug endpoint to force garbage collection."""
            try:
                before_count = gc.get_count()
                collected = gc.collect()
                after_count = gc.get_count()
                
                self.logger.info(f"Manual GC: collected {collected} objects")
                
                return jsonify({
                    'collected': collected,
                    'before_count': before_count,
                    'after_count': after_count,
                    'timestamp': get_current_time_iso()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.flask_app.route('/webhook', methods=['POST'])
        def webhook():
            """Webhook endpoint for Telegram."""
            if not self.bot:
                return jsonify({'error': 'Bot not initialized'}), 500
            
            try:
                json_string = request.get_data().decode('utf-8')
                update = telebot.types.Update.de_json(json_string)
                self.bot.process_new_updates([update])
                return jsonify({'status': 'ok'})
            except Exception as e:
                self.logger.error(f"Webhook processing error: {e}")
                return jsonify({'error': str(e)}), 500
        
        # API endpoints for make.com integration
        @self.flask_app.route('/api/load-data', methods=['POST'])
        def load_data():
            """API endpoint for data loading."""
            try:
                self.logger.info("API: Starting data loading from previous day")
                
                data = request.get_json() or {}
                days_ahead = data.get('days_ahead', 5)
                
                db = SessionLocal()
                try:
                    data_loader = DataLoaderService(db)
                    result = data_loader.load_data_from_previous_day(days_ahead)
                    
                    self.logger.info(f"API: Data loading completed with status: {result['status']}")
                    
                    return jsonify({
                        'success': result['status'] in ['success', 'partial'],
                        'result': result,
                        'timestamp': get_current_time_iso()
                    })
                finally:
                    db.close()
                    
            except Exception as e:
                self.logger.error(f"API: Data loading failed: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
        
        @self.flask_app.route('/api/send-today', methods=['POST'])
        def send_today():
            """API endpoint for sending today's news."""
            try:
                self.logger.info("API: Starting today news sending to all users")
                
                if not self.bot:
                    return jsonify({
                        'success': False,
                        'error': 'Telegram bot not available',
                        'timestamp': get_current_time_iso()
                    }), 500
                
                db = SessionLocal()
                try:
                    today_service = TodayService(db, self.bot)
                    result = today_service.send_today_to_all_users()
                    
                    self.logger.info(f"API: Today news sending completed with status: {result['status']}")
                    
                    return jsonify({
                        'success': result['status'] in ['success', 'partial'],
                        'result': result,
                        'timestamp': get_current_time_iso()
                    })
                finally:
                    db.close()
                    
            except Exception as e:
                self.logger.error(f"API: Today news sending failed: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
        
        @self.flask_app.route('/api/status', methods=['GET'])
        def get_status():
            """API endpoint for application status."""
            try:
                db_status = "unknown"
                try:
                    db = SessionLocal()
                    try:
                        db.execute("SELECT 1")
                        db_status = "connected"
                    finally:
                        db.close()
                except Exception as e:
                    db_status = f"error: {str(e)}"
                
                return jsonify({
                    'api_status': 'running',
                    'mode': self.app_state['mode'],
                    'database_status': db_status,
                    'bot_available': self.bot is not None,
                    'webhook_url': self.webhook_url,
                    'timezone': config.TIMEZONE,
                    'uptime_seconds': time.time() - self.start_time,
                    'initialization_complete': self.app_state['initialization_complete'],
                    'services_started': self.app_state['services_started'],
                    'timestamp': get_current_time_iso()
                })
                
            except Exception as e:
                self.logger.error(f"API: Status check failed: {e}")
                return jsonify({
                    'api_status': 'error',
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
    
    def _setup_webhook_if_needed(self):
        """Setup webhook for production mode."""
        if not self.is_webhook_mode:
            return
        
        self.webhook_url = self._get_webhook_url()
        
        if not self.webhook_url:
            self.logger.error("❌ Webhook URL not configured for webhook mode")
            raise SystemExit(1)
        
        try:
            # Remove existing webhook first
            self.bot.remove_webhook()
            self.logger.info("Removed existing webhook")
            
            # Set new webhook
            result = self.bot.set_webhook(url=self.webhook_url)
            if result:
                self.logger.info(f"✅ Webhook set successfully: {self.webhook_url}")
            else:
                self.logger.error("❌ Failed to set webhook")
                raise SystemExit(1)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to setup webhook: {e}")
            raise SystemExit(1)
    
    def start(self):
        """Start the application with enhanced monitoring."""
        global shutdown_requested
        
        self.logger.info(f"🚀 Starting application in {self.app_state['mode']} mode...")
        
        try:
            if self.is_webhook_mode:
                self._start_webhook_mode()
            else:
                self._start_polling_mode()
                
            self.app_state['services_started'] = True
            self.logger.info("✅ Application started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start application: {e}")
            raise
    
    def _start_webhook_mode(self):
        """Start application in webhook mode."""
        self.logger.info(f"🌐 Starting Flask server on {config.FLASK_HOST}:{config.FLASK_PORT}")
        
        # Run Flask app (this will block)
        self.flask_app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            threaded=True
        )
    
    def _start_polling_mode(self):
        """Start application in polling mode."""
        global shutdown_requested
        
        if self.bot:
            # Start polling in a separate thread
            def start_polling():
                try:
                    self.logger.info("🤖 Starting Telegram bot polling...")
                    while not shutdown_requested:
                        try:
                            self.bot.infinity_polling(none_stop=True, interval=0, timeout=20)
                        except Exception as e:
                            if not shutdown_requested:
                                self.logger.error(f"Telegram bot polling error: {e}")
                                time.sleep(5)  # Wait before retrying
                            else:
                                break
                except Exception as e:
                    self.logger.error(f"Critical polling error: {e}")
            
            self.polling_thread = threading.Thread(target=start_polling, daemon=True)
            self.polling_thread.start()
            
            # Start Flask server for API endpoints
            def start_flask():
                try:
                    self.logger.info(f"🌐 Starting Flask API server on {config.FLASK_HOST}:{config.FLASK_PORT}")
                    self.flask_app.run(
                        host=config.FLASK_HOST,
                        port=config.FLASK_PORT,
                        debug=config.FLASK_DEBUG,
                        threaded=True
                    )
                except Exception as e:
                    if not shutdown_requested:
                        self.logger.error(f"Flask server error: {e}")
            
            self.flask_thread = threading.Thread(target=start_flask, daemon=True)
            self.flask_thread.start()
            
            # Main loop - wait for shutdown signal
            self.logger.info("⏳ Application running - waiting for shutdown signal...")
            while not shutdown_requested:
                time.sleep(1)
    
    def _cleanup_telegram_bot(self):
        """Cleanup Telegram bot resources."""
        self.logger.info("🤖 Cleaning up Telegram bot...")
        
        if self.bot:
            try:
                if self.is_webhook_mode:
                    self.bot.remove_webhook()
                    self.logger.info("Webhook removed")
                else:
                    self.bot.stop_polling()
                    self.logger.info("Bot polling stopped")
            except Exception as e:
                self.logger.error(f"Error stopping bot: {e}")
    
    def _cleanup_flask_app(self):
        """Cleanup Flask application."""
        self.logger.info("🌐 Cleaning up Flask application...")
        # Flask cleanup is handled by the framework
    
    def _cleanup_database(self):
        """Cleanup database connections."""
        self.logger.info("🗄️ Cleaning up database connections...")
        # Database cleanup is handled by SQLAlchemy

def main():
    """Enhanced main entry point with comprehensive error handling."""
    app = None
    
    try:
        app = EnhancedTelegramBotApplication()
        app.initialize()
        app.start()
        
    except KeyboardInterrupt:
        if app and app.logger:
            app.logger.info("Application interrupted by user")
        else:
            print("Application interrupted by user")
    except SystemExit as e:
        if app and app.logger:
            app.logger.info(f"Application exiting with code {e.code}")
        else:
            print(f"Application exiting with code {e.code}")
        sys.exit(e.code)
    except Exception as e:
        if app and app.logger:
            app.logger.error(f"Application failed with unexpected error: {e}", exc_info=True)
        else:
            print(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
