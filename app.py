#!/usr/bin/env python3
"""Forex News Telegram Bot (modular version with database integration)."""

import asyncio
from datetime import datetime, date, timedelta
from typing import Optional

from flask import Flask, request, jsonify
import telebot

from bot.config import Config, setup_logging
from bot.telegram_handlers import TelegramBotManager, RenderKeepAlive, register_handlers
from bot.scraper import ChatGPTAnalyzer, ForexNewsScraper, process_forex_news, MessageFormatter
from bot.database_service import ForexNewsService

config = Config()
logger = setup_logging()
app = Flask(__name__)

bot_manager = TelegramBotManager(config)
bot = bot_manager.bot

keep_alive = RenderKeepAlive(config)

analyzer = ChatGPTAnalyzer(config.chatgpt_api_key)
scraper = ForexNewsScraper(config, analyzer)

# Initialize database service
try:
    db_service = ForexNewsService(config.get_database_url())
    logger.info("Database service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database service: {e}")
    db_service = None

if bot:
    register_handlers(bot, lambda date, impact, debug: process_forex_news_with_db(scraper, bot, config, db_service, date, impact, debug), config)


async def process_forex_news_with_db(scraper, bot, config, db_service, target_date: Optional[datetime] = None, impact_level: str = "high", analysis_required: bool = True, debug: bool = False):
    """Process forex news with database integration. Always store all news for the date in the DB."""
    if not bot or not config.telegram_chat_id:
        logger.error("Cannot process news: Bot or CHAT_ID not configured")
        return [] if debug else None
    try:
        if target_date is None:
            target_date = datetime.now()
        target_date_obj = target_date.date()

        # Always check/store all news for the date in the DB
        if db_service and not db_service.has_news_for_date(target_date_obj, 'all'):
            logger.info(f"No data in database for {target_date_obj}, scraping all impacts...")
            all_news_items = await scraper.scrape_news(target_date, analysis_required, debug)
            if all_news_items and db_service:
                db_service.store_news_items(all_news_items, target_date_obj, 'all')
                logger.info(f"Stored all news for {target_date_obj} in database.")
        else:
            logger.info(f"All news for {target_date_obj} already in database.")

        # Now filter for the requested impact level for output
        if db_service:
            # If user asked for 'all', just return all
            if impact_level == 'all':
                news_items = db_service.get_news_for_date(target_date_obj, 'all')
            else:
                # Filter from 'all' in DB for the requested impact
                all_items = db_service.get_news_for_date(target_date_obj, 'all')
                news_items = [item for item in all_items if item.get('impact') == impact_level]
        else:
            news_items = []

        if debug:
            return news_items

        # Format and send message
        from bot.scraper import MessageFormatter
        message = MessageFormatter.format_news_message(news_items, target_date, impact_level, analysis_required)
        if message.strip():
            from bot.utils import send_long_message
            send_long_message(bot, config.telegram_chat_id, message, parse_mode="HTML")
        else:
            logger.error("Generated message is empty")
        return news_items
    except Exception as e:
        logger.exception("Unexpected error in process_forex_news_with_db: %s", e)
        try:
            error_msg = f"⚠️ Error in Forex news processing: {str(e)}"
            bot.send_message(config.telegram_chat_id, error_msg)
        except Exception:
            logger.exception("Failed to send error notification")
        return [] if debug else None


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
    db_healthy = db_service.health_check() if db_service else False
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "forex-telegram-bot",
        "database": "connected" if db_healthy else "disconnected",
        "ready": True
    }), 200


@app.route('/manual_scrape', methods=['POST'])
def manual_scrape():
    provided_key = request.headers.get('X-API-Key') or request.json.get('api_key')
    if not provided_key or provided_key != config.api_key:
        return jsonify({"error": "Invalid or missing API key"}), 401
    data = request.get_json() or {}
    date_str = data.get('date')
    impact_level = data.get('impact_level', 'high')
    debug = data.get('debug', False)
    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    result = asyncio.run(process_forex_news_with_db(scraper, bot, config, db_service, target_date, impact_level, debug))
    return jsonify({
        "status": "success",
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "impact_level": impact_level,
        "news_count": len(result),
        "news_items": result if debug else "News sent to Telegram",
    })


@app.route('/db/stats', methods=['GET'])
def db_stats():
    """Get database statistics."""
    if not db_service:
        return jsonify({"error": "Database service not available"}), 503

    try:
        # Get stats for the last 30 days
        end_date = date.today()
        start_date = end_date.replace(day=1)  # Start of current month

        stats = db_service.get_date_range_stats(start_date, end_date)
        return jsonify({
            "status": "success",
            "stats": stats,
            "database_healthy": db_service.health_check()
        })
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/db/check/<date_str>', methods=['GET'])
def db_check_date(date_str):
    """Check if data exists for a specific date."""
    if not db_service:
        return jsonify({"error": "Database service not available"}), 503

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        impact_level = request.args.get('impact_level', 'high')

        has_data = db_service.has_news_for_date(target_date, impact_level)
        news_count = len(db_service.get_news_for_date(target_date, impact_level)) if has_data else 0

        return jsonify({
            "date": date_str,
            "impact_level": impact_level,
            "has_data": has_data,
            "news_count": news_count
        })
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Error checking date {date_str}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/db/import', methods=['POST'])
def db_import():
    """Import data for a specific date range."""
    provided_key = request.headers.get('X-API-Key') or request.json.get('api_key')
    if not provided_key or provided_key != config.api_key:
        return jsonify({"error": "Invalid or missing API key"}), 401

    if not db_service:
        return jsonify({"error": "Database service not available"}), 503

    data = request.get_json() or {}
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    impact_level = data.get('impact_level', 'high')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Run import asynchronously
        asyncio.create_task(bulk_import_news(start_date, end_date, impact_level))

        return jsonify({
            "status": "import_started",
            "start_date": start_date_str,
            "end_date": end_date_str,
            "impact_level": impact_level
        })
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Error starting import: {e}")
        return jsonify({"error": str(e)}), 500


async def bulk_import_news(start_date: date, end_date: date, impact_level: str = "high"):
    """Bulk import news for a date range."""
    try:
        current_date = start_date
        total_imported = 0

        while current_date <= end_date:
            try:
                logger.info(f"Importing data for {current_date}")

                # Check if data already exists
                if db_service.has_news_for_date(current_date, impact_level):
                    logger.info(f"Data already exists for {current_date}, skipping...")
                    current_date += timedelta(days=1)
                    continue

                # Scrape and store
                news_items = await scraper.scrape_news(
                    target_date=datetime.combine(current_date, datetime.min.time()),
                    impact_level=impact_level,
                    debug=False
                )

                if news_items:
                    success = db_service.store_news_items(news_items, current_date, impact_level)
                    if success:
                        total_imported += len(news_items)
                        logger.info(f"Imported {len(news_items)} items for {current_date}")

                await asyncio.sleep(2)  # Rate limiting

            except Exception as e:
                logger.error(f"Error importing {current_date}: {e}")

            current_date += timedelta(days=1)

        logger.info(f"Bulk import completed. Total imported: {total_imported}")

    except Exception as e:
        logger.error(f"Bulk import failed: {e}")


@app.route('/status', methods=['GET'])
def status():
    missing_vars = config.validate_required_vars()
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "bot_initialized": bot is not None,
            "chat_id_configured": bool(config.telegram_chat_id),
            "chatgpt_configured": bool(config.chatgpt_api_key),
            "database_configured": bool(config.database_url),
            "render_hostname": config.render_hostname,
            "port": config.port,
            "timezone": config.timezone,
        },
        "missing_env_vars": missing_vars,
        "ready": len(missing_vars) == 0 and bot is not None,
    })


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "Forex News Telegram Bot",
        "status": "running",
        "endpoints": {
            "/ping": "Health check",
            "/status": "Application status",
            "/manual_scrape": "Manual news scraping (POST, requires API key)",
            "/webhook": "Telegram webhook (POST)",
            "/db/stats": "Database statistics (GET)",
            "/db/check/<date>": "Check data for date (GET)",
            "/db/import": "Bulk import data (POST, requires API key)",
        },
    })


def initialize_application():
    """Initialize the application - called both in direct run and gunicorn."""
    logger.info("Starting Forex News Telegram Bot...")
    missing_vars = config.validate_required_vars()
    if missing_vars:
        logger.warning("Missing environment variables: %s", missing_vars)

    # Setup webhook with shorter delay for faster startup
    if bot and config.render_hostname:
        bot_manager.setup_webhook_async()
    else:
        logger.warning("Webhook setup skipped: Bot or hostname not configured")

    logger.info("Application initialized successfully on port %s", config.port)


# Initialize application when module is imported (for gunicorn)
initialize_application()


if __name__ == '__main__':
    # This runs only when called directly (not via gunicorn)
    app.run(host='0.0.0.0', port=config.port, debug=False, threaded=True)
