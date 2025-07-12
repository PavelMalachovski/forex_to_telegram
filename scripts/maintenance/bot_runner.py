
#!/usr/bin/env python3
"""
Универсальный запускатель Telegram бота с поддержкой polling и webhook режимов.
"""

import os
import sys
import time
import logging
import threading
import signal
import atexit
from pathlib import Path
from flask import Flask, jsonify, request
import telebot

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Global variables for application state
app_running = True
flask_app = None
telegram_bot = None
logger = None
bot_mode = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global app_running, logger
    if logger:
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    else:
        print(f"Received signal {signum}, initiating graceful shutdown...")
    app_running = False

def cleanup_on_exit():
    """Cleanup function called on exit."""
    global logger, telegram_bot, bot_mode
    
    # Cleanup webhook if in webhook mode
    if bot_mode == 'webhook' and telegram_bot:
        try:
            telegram_bot.remove_webhook()
            if logger:
                logger.info("✅ Webhook removed on shutdown")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️  Failed to remove webhook on shutdown: {e}")
    
    if logger:
        logger.info("Application cleanup completed")
    else:
        print("Application cleanup completed")

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup_on_exit)

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
    file_handler = logging.FileHandler(log_dir / 'bot.log')
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
    """Create and configure Flask application for webhook mode."""
    app = Flask(__name__)
    
    # Global variables for status tracking
    app_status = {
        'status': 'running',
        'start_time': time.time(),
        'heartbeat_count': 0,
        'last_heartbeat': None,
        'mode': bot_mode
    }
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'uptime': time.time() - app_status['start_time'],
            'mode': bot_mode
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
            'project_root': str(project_root),
            'mode': bot_mode
        }), 200
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Telegram webhook endpoint."""
        global telegram_bot, logger
        
        if not telegram_bot:
            if logger:
                logger.error("Telegram bot not initialized")
            return jsonify({'error': 'Bot not configured'}), 500
        
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            telegram_bot.process_new_updates([update])
            
            if logger:
                logger.debug("Webhook processed successfully")
            
            return jsonify({'status': 'ok'})
        except Exception as e:
            if logger:
                logger.error(f"Webhook error: {e}")
            return jsonify({'error': 'Webhook processing failed'}), 500
    
    return app, app_status

def create_telegram_bot():
    """Create and configure Telegram bot."""
    global logger
    try:
        from app.config import config
        import telebot
        from app.database.connection import SessionLocal
        from app.bot.handlers import BotHandlers
        
        if not config.TELEGRAM_BOT_TOKEN:
            if logger:
                logger.warning("⚠️  TELEGRAM_BOT_TOKEN not configured, bot will not start")
            else:
                print("⚠️  TELEGRAM_BOT_TOKEN not configured, bot will not start")
            return None
            
        # Create bot instance
        bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
        
        # Initialize handlers with database session factory
        if SessionLocal:
            BotHandlers(bot, SessionLocal)
            if logger:
                logger.info("✅ Telegram bot created and handlers registered")
            else:
                print("✅ Telegram bot created and handlers registered")
        else:
            if logger:
                logger.warning("⚠️  Database not available, bot handlers not registered")
            else:
                print("⚠️  Database not available, bot handlers not registered")
        
        return bot
        
    except ImportError as e:
        if logger:
            logger.warning(f"⚠️  Could not import Telegram bot dependencies: {e}")
        else:
            print(f"⚠️  Could not import Telegram bot dependencies: {e}")
        return None
    except Exception as e:
        if logger:
            logger.error(f"❌ Failed to create Telegram bot: {e}")
        else:
            print(f"❌ Failed to create Telegram bot: {e}")
        return None

def setup_webhook():
    """Setup webhook for production deployment."""
    global telegram_bot, logger
    
    if not telegram_bot:
        if logger:
            logger.warning("⚠️  Cannot setup webhook - bot not initialized")
        return False
    
    try:
        # Use webhook manager for consistent webhook setup
        from webhook_manager import WebhookManager
        
        manager = WebhookManager()
        
        # Delete existing webhook first to avoid conflicts
        manager.delete_webhook()
        time.sleep(1)
        
        # Set new webhook
        success = manager.set_webhook()
        
        if success:
            if logger:
                logger.info("✅ Webhook configured successfully")
        else:
            if logger:
                logger.error("❌ Failed to configure webhook")
        
        return success
            
    except Exception as e:
        if logger:
            logger.error(f"❌ Error setting up webhook: {e}")
        return False

def run_flask_server(app, port, logger):
    """Run Flask server in a separate thread."""
    try:
        logger.info(f"Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}", exc_info=True)

def run_polling_mode():
    """Run bot in polling mode."""
    global telegram_bot, logger, app_running
    
    if not telegram_bot:
        if logger:
            logger.error("❌ Cannot start polling - bot not initialized")
        return False
    
    try:
        if logger:
            logger.info("🔄 Starting bot in polling mode...")
        
        # Make sure no webhook is set
        try:
            telegram_bot.remove_webhook()
            time.sleep(1)
            if logger:
                logger.info("✅ Webhook removed for polling mode")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️  Could not remove webhook: {e}")
        
        # Start polling with proper error handling
        while app_running:
            try:
                if logger:
                    logger.info("🔄 Starting polling...")
                
                telegram_bot.polling(
                    none_stop=False,
                    interval=1,
                    timeout=20,
                    long_polling_timeout=20
                )
                
            except Exception as e:
                if app_running:  # Only log if we're still supposed to be running
                    if logger:
                        logger.error(f"❌ Polling error: {e}")
                    time.sleep(5)  # Wait before retrying
                else:
                    break
        
        if logger:
            logger.info("✅ Polling stopped")
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"❌ Critical error in polling mode: {e}")
        return False

def run_webhook_mode():
    """Run bot in webhook mode."""
    global flask_app, telegram_bot, logger, app_running
    
    try:
        # Get port from environment or use default
        port = int(os.getenv('PORT', 8000))
        
        # Create Flask app
        flask_app, app_status = create_flask_app()
        
        # Start Flask server in a separate thread
        flask_thread = threading.Thread(
            target=run_flask_server,
            args=(flask_app, port, logger),
            daemon=True
        )
        flask_thread.start()
        
        if logger:
            logger.info(f"✅ Flask server started on port {port}")
        
        # Setup webhook
        if telegram_bot:
            # Wait a bit for Flask server to start
            time.sleep(2)
            
            webhook_success = setup_webhook()
            if webhook_success:
                if logger:
                    logger.info("✅ Telegram bot webhook configured successfully")
            else:
                if logger:
                    logger.warning("⚠️  Telegram bot webhook setup failed - bot may not receive updates")
        else:
            if logger:
                logger.warning("⚠️  Telegram bot not started (token missing or error)")
        
        # Keep running with heartbeat
        if logger:
            logger.info("Application is running in webhook mode. Use SIGTERM or Ctrl+C to stop.")
        
        try:
            while app_running:
                time.sleep(30)
                if app_running:
                    app_status['heartbeat_count'] += 1
                    app_status['last_heartbeat'] = time.time()
                    if logger:
                        logger.info(f"Application heartbeat #{app_status['heartbeat_count']} - webhook mode")
        except KeyboardInterrupt:
            if logger:
                logger.info("Received keyboard interrupt, shutting down...")
            app_running = False
        
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"❌ Critical error in webhook mode: {e}")
        return False

def main():
    """Main function with mode selection."""
    global app_running, flask_app, telegram_bot, logger, bot_mode
    
    # Setup signal handlers first
    setup_signal_handlers()
    
    # Setup logging
    logger = setup_enhanced_logging()
    
    # Determine bot mode
    bot_mode = os.getenv('BOT_MODE', 'polling').lower()
    
    if bot_mode not in ['polling', 'webhook']:
        logger.error(f"❌ Invalid BOT_MODE: {bot_mode}. Must be 'polling' or 'webhook'")
        return 1
    
    logger.info(f"=== Forex Bot Starting in {bot_mode.upper()} mode ===")
    
    try:
        # Test imports and database
        logger.info(f"Project root: {project_root}")
        
        try:
            from app.config import Config
            logger.info("✅ Successfully imported Config")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import Config: {e}")
        
        try:
            from app.database.connection import get_db, init_database
            logger.info("✅ Successfully imported database connection functions")
            
            # Initialize database
            try:
                init_database()
                logger.info("✅ Database initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️  Database initialization failed: {e}")
                
        except ImportError as e:
            logger.warning(f"⚠️  Could not import database connection: {e}")
        
        # Create Telegram bot
        telegram_bot = create_telegram_bot()
        
        if not telegram_bot:
            logger.error("❌ Failed to create Telegram bot")
            return 1
        
        # Run in selected mode
        if bot_mode == 'polling':
            success = run_polling_mode()
        else:  # webhook
            success = run_webhook_mode()
        
        if success:
            logger.info(f"=== Bot shutdown completed successfully ({bot_mode} mode) ===")
            return 0
        else:
            logger.error(f"=== Bot failed in {bot_mode} mode ===")
            return 1
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
