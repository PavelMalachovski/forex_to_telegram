
"""
Flask API server for make.com integration.
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import config
from app.utils.logging_config import setup_logging
from app.utils.timezone_utils import get_current_time_iso
from app.database.connection import init_database, SessionLocal
from app.services.data_loader_service import DataLoaderService
from app.services.today_service import TodayService
import telebot

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize bot
bot = None
if config.TELEGRAM_BOT_TOKEN:
    try:
        bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
        logger.info("Telegram bot initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        bot = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': get_current_time_iso(),
        'bot_available': bot is not None
    })

@app.route('/api/load-data', methods=['POST'])
def load_data():
    """
    Load forex data starting from previous day.
    This endpoint is designed to be called by make.com at 05:00.
    """
    try:
        logger.info("API: Starting data loading from previous day")
        
        # Get optional parameters
        data = request.get_json() or {}
        days_ahead = data.get('days_ahead', 5)
        
        # Initialize database session
        db = SessionLocal()
        
        try:
            # Load data using service
            data_loader = DataLoaderService(db)
            result = data_loader.load_data_from_previous_day(days_ahead)
            
            logger.info(f"API: Data loading completed with status: {result['status']}")
            
            return jsonify({
                'success': result['status'] in ['success', 'partial'],
                'result': result,
                'timestamp': get_current_time_iso()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"API: Data loading failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': get_current_time_iso()
        }), 500

@app.route('/api/send-today', methods=['POST'])
def send_today():
    """
    Send today's news to all active users.
    This endpoint is designed to be called by make.com at 07:00.
    """
    try:
        logger.info("API: Starting today news sending to all users")
        
        if not bot:
            return jsonify({
                'success': False,
                'error': 'Telegram bot not available',
                'timestamp': get_current_time_iso()
            }), 500
        
        # Initialize database session
        db = SessionLocal()
        
        try:
            # Send today news using service
            today_service = TodayService(db, bot)
            result = today_service.send_today_to_all_users()
            
            logger.info(f"API: Today news sending completed with status: {result['status']}")
            
            return jsonify({
                'success': result['status'] in ['success', 'partial'],
                'result': result,
                'timestamp': get_current_time_iso()
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"API: Today news sending failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': get_current_time_iso()
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get API server status and configuration."""
    try:
        db = SessionLocal()
        
        try:
            # Test database connection
            db.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        finally:
            db.close()
        
        return jsonify({
            'api_status': 'running',
            'database_status': db_status,
            'bot_available': bot is not None,
            'timezone': config.TIMEZONE,
            'timestamp': get_current_time_iso()
        })
        
    except Exception as e:
        logger.error(f"API: Status check failed: {e}")
        return jsonify({
            'api_status': 'error',
            'error': str(e),
            'timestamp': get_current_time_iso()
        }), 500

if __name__ == '__main__':
    try:
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Start Flask app
        logger.info(f"Starting API server on {config.FLASK_HOST}:{config.FLASK_PORT}")
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG
        )
        
    except Exception as e:
        logger.error(f"API server failed to start: {e}")
        sys.exit(1)
