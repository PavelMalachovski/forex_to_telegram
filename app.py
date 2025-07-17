#!/usr/bin/env python3
"""Forex News Telegram Bot (modular version with PostgreSQL integration)."""

import asyncio
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify
import telebot

from bot.config import Config, setup_logging
from bot.telegram_handlers import initialize_bot_with_scheduler
from bot.scraper import scrape_and_send_forex_data
from bot.database import get_db_manager

config = Config()
logger = setup_logging()
app = Flask(__name__)

# Initialize bot with scheduler and database integration
bot = initialize_bot_with_scheduler()


@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot:
        logger.error("Webhook called but bot not initialized")
        return jsonify({"error": "Bot not initialized"}), 500
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "bot_status": "initialized" if bot else "not_initialized",
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Render deployment."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "forex-telegram-bot",
        "ready": True
    }), 200


@app.route('/manual_scrape', methods=['POST'])
def manual_scrape():
    provided_key = request.headers.get('X-API-Key') or request.json.get('api_key')
    if not provided_key or provided_key != config.api_key:
        return jsonify({"error": "Invalid or missing API key"}), 401
    
    data = request.get_json() or {}
    start_date_str = data.get('start_date') or data.get('date')
    end_date_str = data.get('end_date')
    
    # Default to today if no date provided
    if not start_date_str:
        start_date = date.today()
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
    
    # Default end_date to start_date if not provided
    if not end_date_str:
        end_date = start_date
    else:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
    
    if start_date > end_date:
        return jsonify({"error": "start_date cannot be after end_date"}), 400
    
    try:
        # Use the new database-integrated scraping function
        scrape_and_send_forex_data(start_date, end_date)
        
        # Get the scraped data from database for response
        db_manager = get_db_manager()
        events = db_manager.get_events_by_date_range(start_date, end_date)
        
        return jsonify({
            "status": "success",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "events_count": len(events),
            "message": "Data scraped and sent to Telegram successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in manual scrape: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/status', methods=['GET'])
def status():
    missing_vars = config.validate_required_vars()
    
    # Check database connection
    db_status = "unknown"
    try:
        db_manager = get_db_manager()
        # Try a simple query to test connection
        db_manager.check_data_exists(date.today(), date.today())
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "bot_initialized": bot is not None,
            "chat_id_configured": bool(config.telegram_chat_id),
            "openai_configured": bool(config.openai_api_key),
            "render_hostname": config.render_hostname,
            "port": config.port,
            "timezone": config.timezone,
            "database_url_configured": bool(config.database_url),
            "database_status": db_status,
        },
        "missing_env_vars": missing_vars,
        "ready": len(missing_vars) == 0 and bot is not None and db_status == "connected",
    })


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "Forex News Telegram Bot with PostgreSQL",
        "status": "running",
        "features": [
            "PostgreSQL database integration",
            "Daily scheduled scraping at 03:00 UTC",
            "Manual execution with date ranges",
            "Data deduplication and caching",
            "Telegram bot integration"
        ],
        "endpoints": {
            "/ping": "Health check",
            "/status": "Application status with database info",
            "/manual_scrape": "Manual news scraping with date range (POST, requires API key)",
            "/webhook": "Telegram webhook (POST)",
            "/health": "Health check for deployment"
        },
    })


def initialize_application():
    """Initialize the application - called both in direct run and gunicorn."""
    logger.info("Starting Forex News Telegram Bot with PostgreSQL integration...")
    missing_vars = config.validate_required_vars()
    if missing_vars:
        logger.warning("Missing environment variables: %s", missing_vars)
    
    # Initialize database tables
    try:
        db_manager = get_db_manager()
        db_manager.create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    if bot:
        logger.info("Bot initialized with scheduler and database integration")
    else:
        logger.warning("Bot initialization failed")
    
    logger.info("Application initialized successfully on port %s", config.port)


# Initialize application when module is imported (for gunicorn)
initialize_application()


if __name__ == '__main__':
    # This runs only when called directly (not via gunicorn)
    app.run(host='0.0.0.0', port=config.port, debug=False, threaded=True)
