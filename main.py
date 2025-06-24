
"""
Main application entry point for Telegram bot.
Supports both webhook (production) and polling (development) modes.
"""

import os
import sys
import signal
import telebot
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import threading

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.logging_config import setup_logging
from app.database.connection import init_database, SessionLocal
from app.bot.handlers import BotHandlers
from app.services.data_loader_service import DataLoaderService
from app.services.today_service import TodayService

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Unified Telegram bot application with webhook and polling support."""
    
    def __init__(self):
        self.bot = None
        self.bot_handlers = None
        self.flask_app = None
        self.is_webhook_mode = self._is_webhook_mode()
        self.webhook_url = None
        
    def _is_webhook_mode(self):
        """Determine if we should use webhook mode."""
        # Use webhook mode if we're on Render.com or WEBHOOK_MODE is explicitly set
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
        """Initialize the application."""
        logger.info(f"Initializing Telegram Bot application in {'webhook' if self.is_webhook_mode else 'polling'} mode...")
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Initialize database
        try:
            init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            sys.exit(1)
        
        # Initialize Telegram bot
        if config.TELEGRAM_BOT_TOKEN:
            try:
                self.bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
                self.bot_handlers = BotHandlers(self.bot, lambda: SessionLocal())
                logger.info("Telegram bot initialized successfully")
                
                # Test bot token validity only if not using placeholder token
                if not config.TELEGRAM_BOT_TOKEN.startswith('your_'):
                    try:
                        self.bot.get_me()
                        logger.info("Bot token validated successfully")
                    except Exception as e:
                        logger.warning(f"Bot token validation failed: {e}")
                        if self.is_webhook_mode:
                            logger.error("Invalid bot token in production mode")
                            sys.exit(1)
                        else:
                            logger.warning("Continuing in development mode with invalid token")
                else:
                    logger.warning("Using placeholder bot token - replace with real token for production")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                sys.exit(1)
        else:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            sys.exit(1)
        
        # Initialize Flask app for webhook mode or API endpoints
        self._initialize_flask_app()
        
        # Setup webhook if in webhook mode
        if self.is_webhook_mode:
            self._setup_webhook()
        
        logger.info("Application initialized successfully")
    
    def _initialize_flask_app(self):
        """Initialize Flask application."""
        self.flask_app = Flask(__name__)
        
        # Health check endpoint
        @self.flask_app.route('/health', methods=['GET'])
        @self.flask_app.route('/ping', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'mode': 'webhook' if self.is_webhook_mode else 'polling',
                'timestamp': datetime.now().isoformat(),
                'bot_available': self.bot is not None
            })
        
        # Webhook endpoint for Telegram
        @self.flask_app.route('/webhook', methods=['POST'])
        def webhook():
            if not self.bot:
                return jsonify({'error': 'Bot not initialized'}), 500
            
            try:
                json_string = request.get_data().decode('utf-8')
                update = telebot.types.Update.de_json(json_string)
                self.bot.process_new_updates([update])
                return jsonify({'status': 'ok'})
            except Exception as e:
                logger.error(f"Webhook processing error: {e}")
                return jsonify({'error': str(e)}), 500
        
        # API endpoints for make.com integration
        @self.flask_app.route('/api/load-data', methods=['POST'])
        def load_data():
            try:
                logger.info("API: Starting data loading from previous day")
                
                data = request.get_json() or {}
                days_ahead = data.get('days_ahead', 5)
                
                db = SessionLocal()
                try:
                    data_loader = DataLoaderService(db)
                    result = data_loader.load_data_from_previous_day(days_ahead)
                    
                    logger.info(f"API: Data loading completed with status: {result['status']}")
                    
                    return jsonify({
                        'success': result['status'] in ['success', 'partial'],
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"API: Data loading failed: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.flask_app.route('/api/send-today', methods=['POST'])
        def send_today():
            try:
                logger.info("API: Starting today news sending to all users")
                
                if not self.bot:
                    return jsonify({
                        'success': False,
                        'error': 'Telegram bot not available',
                        'timestamp': datetime.now().isoformat()
                    }), 500
                
                db = SessionLocal()
                try:
                    today_service = TodayService(db, self.bot)
                    result = today_service.send_today_to_all_users()
                    
                    logger.info(f"API: Today news sending completed with status: {result['status']}")
                    
                    return jsonify({
                        'success': result['status'] in ['success', 'partial'],
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"API: Today news sending failed: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.flask_app.route('/api/status', methods=['GET'])
        def get_status():
            try:
                db = SessionLocal()
                try:
                    db.execute("SELECT 1")
                    db_status = "connected"
                except Exception as e:
                    db_status = f"error: {str(e)}"
                finally:
                    db.close()
                
                return jsonify({
                    'api_status': 'running',
                    'mode': 'webhook' if self.is_webhook_mode else 'polling',
                    'database_status': db_status,
                    'bot_available': self.bot is not None,
                    'webhook_url': self.webhook_url,
                    'timezone': config.TIMEZONE,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"API: Status check failed: {e}")
                return jsonify({
                    'api_status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
    
    def _setup_webhook(self):
        """Setup webhook for production mode."""
        self.webhook_url = self._get_webhook_url()
        
        if not self.webhook_url:
            logger.error("Webhook URL not configured for webhook mode")
            sys.exit(1)
        
        try:
            # Remove existing webhook first
            self.bot.remove_webhook()
            logger.info("Removed existing webhook")
            
            # Set new webhook
            result = self.bot.set_webhook(url=self.webhook_url)
            if result:
                logger.info(f"Webhook set successfully: {self.webhook_url}")
            else:
                logger.error("Failed to set webhook")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
            sys.exit(1)
    
    def start(self):
        """Start the application."""
        logger.info(f"Starting Telegram Bot application in {'webhook' if self.is_webhook_mode else 'polling'} mode...")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        if self.is_webhook_mode:
            # Start Flask server for webhook mode
            logger.info(f"Starting Flask server on {config.FLASK_HOST}:{config.FLASK_PORT}")
            self.flask_app.run(
                host=config.FLASK_HOST,
                port=config.FLASK_PORT,
                debug=config.FLASK_DEBUG
            )
        else:
            # Start polling in a separate thread and Flask server for API
            if self.bot:
                def start_polling():
                    try:
                        logger.info("Starting Telegram bot polling...")
                        self.bot.infinity_polling(none_stop=True, interval=0, timeout=20)
                    except Exception as e:
                        logger.error(f"Telegram bot polling error: {e}")
                
                # Start polling in background thread
                polling_thread = threading.Thread(target=start_polling, daemon=True)
                polling_thread.start()
                
                # Start Flask server for API endpoints
                logger.info(f"Starting Flask API server on {config.FLASK_HOST}:{config.FLASK_PORT}")
                self.flask_app.run(
                    host=config.FLASK_HOST,
                    port=config.FLASK_PORT,
                    debug=config.FLASK_DEBUG
                )
    
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Telegram Bot application...")
        
        if self.bot:
            try:
                if self.is_webhook_mode:
                    # Remove webhook
                    self.bot.remove_webhook()
                    logger.info("Webhook removed")
                else:
                    # Stop polling
                    self.bot.stop_polling()
                    logger.info("Telegram bot polling stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
        
        logger.info("Application stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point."""
    try:
        app = TelegramBotApplication()
        app.initialize()
        app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
