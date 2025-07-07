
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

# Setup basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/forex_bot_postgresql/logs/enhanced_app.log'),
        logging.StreamHandler()
    ]
)

class SignalHandler:
    """Enhanced signal handler with detailed logging."""
    
    def __init__(self, timeout=25):
        self.timeout = timeout
        self.shutdown_requested = False
        self.cleanup_callbacks = []
        self.logger = logging.getLogger(__name__)
        
    def setup(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.logger.info("Signal handlers registered")
        
    def _signal_handler(self, signum, frame):
        """Handle termination signals with detailed logging."""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received signal {signum} ({signal_name}) - initiating graceful shutdown")
        
        # Log stack trace for debugging
        stack_trace = ''.join(traceback.format_stack(frame))
        self.logger.info(f"Signal received at:\n{stack_trace}")
        
        # Log system state
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024
            
            self.logger.info(f"System state at termination: "
                           f"Memory: {memory.percent:.1f}%, "
                           f"CPU: {cpu_percent:.1f}%, "
                           f"Process Memory: {process_memory:.1f}MB")
        except Exception as e:
            self.logger.error(f"Failed to log system state: {e}")
        
        self.shutdown_requested = True
        self._cleanup()
        
    def _cleanup(self):
        """Execute cleanup callbacks."""
        self.logger.info("Starting cleanup process")
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Cleanup callback error: {e}")
        self.logger.info("Cleanup completed")
        
    def register_cleanup(self, callback):
        """Register cleanup callback."""
        self.cleanup_callbacks.append(callback)
        
    def is_shutdown_requested(self):
        """Check if shutdown was requested."""
        return self.shutdown_requested

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
        self.health_monitor = None
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
        # Use protected section for initialization
        with protect_critical_section():
            self._setup_logging()
            self._setup_signal_handling()
            self._setup_health_monitoring()
            self._validate_configuration()
            self._initialize_database()
            self._initialize_telegram_bot()
            self._initialize_flask_app()
            self._setup_webhook_if_needed()
            
            self.app_state['initialization_complete'] = True
            self.logger.info("Application initialization completed successfully")
            log_event(self.logger, "app_initialized", "Application initialized", 
                     mode=self.app_state['mode'], uptime=time.time() - self.start_time)
    
    def _setup_logging(self):
        """Setup enhanced logging system."""
        self.logger = setup_enhanced_logging()
        self.logger.info("Enhanced logging system initialized")
    
    def _setup_signal_handling(self):
        """Setup signal handling for graceful shutdown."""
        self.shutdown_handler = setup_signal_handling(timeout=30)
        
        # Register cleanup callbacks
        register_cleanup_callback(self._cleanup_telegram_bot, "telegram_bot_cleanup")
        register_cleanup_callback(self._cleanup_flask_app, "flask_app_cleanup")
        register_cleanup_callback(self._cleanup_database, "database_cleanup")
        register_cleanup_callback(self._save_final_state, "save_final_state")
        
        self.logger.info("Signal handling configured")
    
    def _setup_health_monitoring(self):
        """Setup health monitoring system."""
        self.health_monitor = get_health_monitor()
        
        # Register custom health checks
        register_health_check("telegram_bot", self._check_telegram_bot_health, 
                            "Check Telegram bot connectivity")
        register_health_check("flask_app", self._check_flask_app_health,
                            "Check Flask application health")
        
        self.logger.info("Health monitoring configured")
    
    def _check_telegram_bot_health(self) -> tuple:
        """Health check for Telegram bot."""
        if not self.bot:
            return False, "Telegram bot not initialized", {}
        
        try:
            # Test bot connectivity
            start_time = time.time()
            bot_info = self.bot.get_me()
            response_time = (time.time() - start_time) * 1000
            
            return True, f"Bot healthy: @{bot_info.username}", {
                'bot_id': bot_info.id,
                'bot_username': bot_info.username,
                'response_time_ms': response_time
            }
        except Exception as e:
            return False, f"Bot health check failed: {str(e)}", {'error': str(e)}
    
    def _check_flask_app_health(self) -> tuple:
        """Health check for Flask application."""
        if not self.flask_app:
            return False, "Flask app not initialized", {}
        
        try:
            # Check if Flask app is properly configured
            with self.flask_app.app_context():
                return True, "Flask app healthy", {
                    'debug_mode': self.flask_app.debug,
                    'testing': self.flask_app.testing
                }
        except Exception as e:
            return False, f"Flask health check failed: {str(e)}", {'error': str(e)}
    
    def _validate_configuration(self):
        """Validate application configuration."""
        self.logger.info("Validating configuration...")
        
        if not config.validate():
            self.logger.error("Configuration validation failed")
            raise SystemExit(1)
        
        self.logger.info("Configuration validated successfully")
    
    def _initialize_database(self):
        """Initialize database connection."""
        self.logger.info("Initializing database...")
        
        try:
            init_database()
            self.logger.info("Database initialized successfully")
            log_event(self.logger, "database_initialized", "Database connection established",
                     database_url=config.DATABASE_URL.split('@')[0] + '@***')
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise SystemExit(1)
    
    def _initialize_telegram_bot(self):
        """Initialize Telegram bot."""
        self.logger.info("Initializing Telegram bot...")
        
        if not config.TELEGRAM_BOT_TOKEN:
            self.logger.error("TELEGRAM_BOT_TOKEN not configured")
            raise SystemExit(1)
        
        try:
            self.bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
            self.bot_handlers = BotHandlers(self.bot, lambda: SessionLocal())
            
            # Test bot token validity
            if not config.TELEGRAM_BOT_TOKEN.startswith('your_'):
                try:
                    bot_info = self.bot.get_me()
                    self.logger.info(f"Bot token validated: @{bot_info.username}")
                    log_event(self.logger, "bot_validated", "Bot token validated",
                             bot_id=bot_info.id, bot_username=bot_info.username)
                except Exception as e:
                    self.logger.warning(f"Bot token validation failed: {e}")
                    if self.is_webhook_mode:
                        self.logger.error("Invalid bot token in production mode")
                        raise SystemExit(1)
            else:
                self.logger.warning("Using placeholder bot token")
            
            self.logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
            raise SystemExit(1)
    
    def _initialize_flask_app(self):
        """Initialize Flask application with enhanced endpoints."""
        self.logger.info("Initializing Flask application...")
        
        self.flask_app = Flask(__name__)
        self._setup_flask_routes()
        
        self.logger.info("Flask application initialized")
    
    def _setup_flask_routes(self):
        """Setup Flask routes with enhanced health and monitoring endpoints."""
        
        @self.flask_app.route('/health', methods=['GET'])
        @self.flask_app.route('/ping', methods=['GET'])
        def health_check():
            """Basic health check endpoint."""
            try:
                health_summary = self.health_monitor.get_health_summary()
                status_code = 200 if health_summary['overall_status'] == 'healthy' else 503
                
                return jsonify({
                    'status': health_summary['overall_status'],
                    'timestamp': get_current_time_iso(),
                    'uptime_seconds': health_summary['uptime_seconds'],
                    'mode': self.app_state['mode'],
                    'checks_summary': health_summary['summary']
                }), status_code
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
        
        @self.flask_app.route('/health/detailed', methods=['GET'])
        def detailed_health_check():
            """Detailed health check with all metrics."""
            try:
                health_summary = self.health_monitor.get_health_summary()
                status_code = 200 if health_summary['overall_status'] == 'healthy' else 503
                return jsonify(health_summary), status_code
            except Exception as e:
                self.logger.error(f"Detailed health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': get_current_time_iso()
                }), 500
        
        @self.flask_app.route('/metrics', methods=['GET'])
        def metrics():
            """Prometheus-style metrics endpoint."""
            try:
                health_summary = self.health_monitor.get_health_summary()
                metrics_text = self._format_prometheus_metrics(health_summary)
                return metrics_text, 200, {'Content-Type': 'text/plain'}
            except Exception as e:
                self.logger.error(f"Metrics endpoint failed: {e}")
                return f"# Error generating metrics: {str(e)}\n", 500
        
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
                with log_with_context(self.logger, request_id=f"load-{int(time.time())}") as ctx_logger:
                    ctx_logger.info("API: Starting data loading from previous day")
                    
                    data = request.get_json() or {}
                    days_ahead = data.get('days_ahead', 5)
                    
                    db = SessionLocal()
                    try:
                        data_loader = DataLoaderService(db)
                        result = data_loader.load_data_from_previous_day(days_ahead)
                        
                        ctx_logger.info(f"API: Data loading completed with status: {result['status']}")
                        log_event(ctx_logger, "data_load_completed", "Data loading completed",
                                 status=result['status'], days_ahead=days_ahead)
                        
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
                with log_with_context(self.logger, request_id=f"today-{int(time.time())}") as ctx_logger:
                    ctx_logger.info("API: Starting today news sending to all users")
                    
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
                        
                        ctx_logger.info(f"API: Today news sending completed with status: {result['status']}")
                        log_event(ctx_logger, "today_news_sent", "Today news sent to users",
                                 status=result['status'])
                        
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
    
    def _format_prometheus_metrics(self, health_summary):
        """Format health data as Prometheus metrics."""
        metrics = []
        
        # Overall health
        overall_healthy = 1 if health_summary['overall_status'] == 'healthy' else 0
        metrics.append(f"app_health_status {overall_healthy}")
        
        # Uptime
        metrics.append(f"app_uptime_seconds {health_summary['uptime_seconds']}")
        
        # System metrics
        if 'metrics' in health_summary:
            sys_metrics = health_summary['metrics']
            metrics.append(f"system_cpu_percent {sys_metrics.get('cpu_percent', 0)}")
            metrics.append(f"system_memory_percent {sys_metrics.get('memory_percent', 0)}")
            metrics.append(f"system_disk_percent {sys_metrics.get('disk_percent', 0)}")
        
        # Check results
        for check_name, check_result in health_summary.get('checks', {}).items():
            check_healthy = 1 if check_result['status'] == 'healthy' else 0
            metrics.append(f'health_check_status{{check="{check_name}"}} {check_healthy}')
            metrics.append(f'health_check_duration_ms{{check="{check_name}"}} {check_result["duration_ms"]}')
        
        return '\n'.join(metrics) + '\n'
    
    def _setup_webhook_if_needed(self):
        """Setup webhook for production mode."""
        if not self.is_webhook_mode:
            return
        
        self.webhook_url = self._get_webhook_url()
        
        if not self.webhook_url:
            self.logger.error("Webhook URL not configured for webhook mode")
            raise SystemExit(1)
        
        try:
            # Remove existing webhook first
            self.bot.remove_webhook()
            self.logger.info("Removed existing webhook")
            
            # Set new webhook
            result = self.bot.set_webhook(url=self.webhook_url)
            if result:
                self.logger.info(f"Webhook set successfully: {self.webhook_url}")
                log_event(self.logger, "webhook_configured", "Webhook configured",
                         webhook_url=self.webhook_url)
            else:
                self.logger.error("Failed to set webhook")
                raise SystemExit(1)
                
        except Exception as e:
            self.logger.error(f"Failed to setup webhook: {e}")
            raise SystemExit(1)
    
    def start(self):
        """Start the application with enhanced monitoring."""
        self.logger.info(f"Starting application in {self.app_state['mode']} mode...")
        
        try:
            if self.is_webhook_mode:
                self._start_webhook_mode()
            else:
                self._start_polling_mode()
                
            self.app_state['services_started'] = True
            log_event(self.logger, "app_started", "Application started successfully",
                     mode=self.app_state['mode'])
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            raise
    
    def _start_webhook_mode(self):
        """Start application in webhook mode."""
        self.logger.info(f"Starting Flask server on {config.FLASK_HOST}:{config.FLASK_PORT}")
        
        # Run Flask app (this will block)
        self.flask_app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            threaded=True
        )
    
    def _start_polling_mode(self):
        """Start application in polling mode."""
        if self.bot:
            # Start polling in a separate thread
            def start_polling():
                try:
                    self.logger.info("Starting Telegram bot polling...")
                    while not is_shutdown_requested():
                        try:
                            self.bot.infinity_polling(none_stop=True, interval=0, timeout=20)
                        except Exception as e:
                            if not is_shutdown_requested():
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
                    self.logger.info(f"Starting Flask API server on {config.FLASK_HOST}:{config.FLASK_PORT}")
                    self.flask_app.run(
                        host=config.FLASK_HOST,
                        port=config.FLASK_PORT,
                        debug=config.FLASK_DEBUG,
                        threaded=True
                    )
                except Exception as e:
                    if not is_shutdown_requested():
                        self.logger.error(f"Flask server error: {e}")
            
            self.flask_thread = threading.Thread(target=start_flask, daemon=True)
            self.flask_thread.start()
            
            # Main loop - wait for shutdown signal
            self.logger.info("Application running - waiting for shutdown signal...")
            while not is_shutdown_requested():
                time.sleep(1)
    
    def _cleanup_telegram_bot(self):
        """Cleanup Telegram bot resources."""
        self.logger.info("Cleaning up Telegram bot...")
        
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
        self.logger.info("Cleaning up Flask application...")
        # Flask cleanup is handled by the framework
    
    def _cleanup_database(self):
        """Cleanup database connections."""
        self.logger.info("Cleaning up database connections...")
        # Database cleanup is handled by SQLAlchemy
    
    def _save_final_state(self):
        """Save final application state."""
        self.logger.info("Saving final application state...")
        
        final_state = {
            **self.app_state,
            'shutdown_time': datetime.utcnow().isoformat(),
            'total_uptime_seconds': time.time() - self.start_time
        }
        
        if self.shutdown_handler:
            self.shutdown_handler.save_application_state(final_state)
        
        # Save health report
        if self.health_monitor:
            try:
                self.health_monitor.save_health_report()
            except Exception as e:
                self.logger.error(f"Failed to save health report: {e}")

def main():
    """Enhanced main entry point with comprehensive error handling."""
    app = None
    
    try:
        app = EnhancedTelegramBotApplication()
        
        # Load previous state if available
        if app.shutdown_handler:
            previous_state = app.shutdown_handler.load_application_state()
            if previous_state:
                app.logger.info(f"Loaded previous application state from {previous_state.get('shutdown_time', 'unknown')}")
        
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
