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
from bot.daily_digest import DailyDigestScheduler
from bot.notification_scheduler import NotificationScheduler
from sqlalchemy import text

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

# Initialize daily digest scheduler
digest_scheduler = None
if db_service and bot:
    try:
        digest_scheduler = DailyDigestScheduler(db_service, bot, config)
        logger.info("Daily digest scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize daily digest scheduler: {e}")

# Initialize notification scheduler
notification_scheduler = None
if db_service and bot:
    try:
        notification_scheduler = NotificationScheduler(db_service, bot, config)
        logger.info("Notification scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize notification scheduler: {e}")

if bot:
    register_handlers(bot, lambda date, impact, analysis, debug, user_id=None: process_forex_news_with_db(scraper, bot, config, db_service, date, impact, analysis, debug, user_id), config, db_service, digest_scheduler)


async def process_forex_news_with_db(scraper, bot, config, db_service, target_date: Optional[datetime] = None, impact_level: str = "high", analysis_required: bool = True, debug: bool = False, user_id: Optional[int] = None):
    """Process forex news with database integration. Always store all news for the date in the DB."""
    if not bot:
        logger.error("Cannot process news: Bot not configured")
        return [] if debug else None

    # Get user preferences if user_id is provided
    user_currencies = None
    user_impact_levels = None
    user_analysis_required = analysis_required

    if user_id and db_service:
        try:
            user = db_service.get_or_create_user(user_id)
            user_currencies = user.get_currencies_list()
            user_impact_levels = user.get_impact_levels_list()
            user_analysis_required = user.analysis_required
        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")

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
            # Get all items from database
            all_items = db_service.get_news_for_date(target_date_obj, 'all')

            if impact_level == 'all':
                # Filter by user's selected impact levels
                if user_impact_levels:
                    news_items = [item for item in all_items if item.get('impact') in user_impact_levels]
                else:
                    # Default to high impact if no user preferences
                    news_items = [item for item in all_items if item.get('impact') == 'high']
            else:
                # Filter for specific impact level
                news_items = [item for item in all_items if item.get('impact') == impact_level]
        else:
            news_items = []

        if debug:
            return news_items

        # Format and send message
        from bot.scraper import MessageFormatter
        message = MessageFormatter.format_news_message(
            news_items,
            target_date,
            impact_level,
            user_analysis_required,
            user_currencies if user_currencies else None
        )

        if message.strip():
            from bot.utils import send_long_message
            # Use user_id if provided, otherwise use config.telegram_chat_id
            chat_id = user_id if user_id else config.telegram_chat_id
            if chat_id:
                send_long_message(bot, chat_id, message, parse_mode="HTML")
            else:
                logger.error("No chat_id available for sending message")
        else:
            logger.error("Generated message is empty")
        return news_items
    except Exception as e:
        logger.exception("Unexpected error in process_forex_news_with_db: %s", e)
        try:
            error_msg = f"⚠️ Error in Forex news processing: {str(e)}"
            chat_id = user_id if user_id else config.telegram_chat_id
            if chat_id:
                bot.send_message(chat_id, error_msg)
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
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint for Render.com."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "bot_initialized": bot is not None,
        "database_available": db_service is not None,
        "digest_scheduler_running": digest_scheduler.get_scheduler_status()['running'] if digest_scheduler else False
    })


@app.route('/health', methods=['GET'])
def health():
    """Detailed health check endpoint."""
    try:
        db_healthy = db_service.health_check() if db_service else False
        scheduler_status = digest_scheduler.get_scheduler_status() if digest_scheduler else {'running': False, 'jobs': []}

        return jsonify({
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "bot": bot is not None,
                "database": db_healthy,
                "digest_scheduler": scheduler_status['running'],
                "webhook": config.telegram_bot_token is not None
            },
            "scheduler": scheduler_status
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/manual_scrape', methods=['POST'])
def manual_scrape():
    """Manual scraping endpoint for testing."""
    try:
        data = request.get_json() or {}
        date_str = data.get('date')
        impact_level = data.get('impact_level', 'high')
        analysis_required = data.get('analysis_required', True)

        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        result = asyncio.run(process_forex_news_with_db(
            scraper, bot, config, db_service,
            target_date, impact_level, analysis_required, debug=True
        ))

        return jsonify({
            "status": "success",
            "news_count": len(result) if result else 0,
            "date": date_str or "today"
        })
    except Exception as e:
        logger.error(f"Manual scrape failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/db/stats', methods=['GET'])
def db_stats():
    """Get database statistics."""
    if not db_service:
        return jsonify({"error": "Database service not available"}), 500

    try:
        # Get date range for stats (last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        stats = db_service.get_date_range_stats(start_date, end_date)

        return jsonify({
            "status": "success",
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Database stats failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/db/check/<date_str>', methods=['GET'])
def db_check_date(date_str):
    """Check if news exists for a specific date."""
    if not db_service:
        return jsonify({"error": "Database service not available"}), 500

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Check for different impact levels
        impact_levels = ['high', 'medium', 'low', 'all']
        results = {}

        for impact in impact_levels:
            has_news = db_service.has_news_for_date(target_date, impact)
            if has_news:
                news_items = db_service.get_news_for_date(target_date, impact)
                results[impact] = {
                    "exists": True,
                    "count": len(news_items)
                }
            else:
                results[impact] = {
                    "exists": False,
                    "count": 0
                }

        return jsonify({
            "status": "success",
            "date": date_str,
            "results": results
        })
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/db/import', methods=['POST'])
def db_import():
    """Bulk import news for a date range."""
    if not db_service:
        return jsonify({"error": "Database service not available"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        impact_level = data.get('impact_level', 'high')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "start_date and end_date are required"}), 400

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if start_date > end_date:
            return jsonify({"error": "start_date must be before or equal to end_date"}), 400

        # Start the bulk import process
        asyncio.run(bulk_import_news(start_date, end_date, impact_level))

        return jsonify({
            "status": "success",
            "message": f"Bulk import started for {start_date_str} to {end_date_str}",
            "impact_level": impact_level
        })
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Bulk import failed: {e}")
        return jsonify({"error": str(e)}), 500


async def bulk_import_news(start_date: date, end_date: date, impact_level: str = "high"):
    """Bulk import news for a date range."""
    if not db_service:
        logger.error("Database service not available for bulk import")
        return

    try:
        current_date = start_date
        total_imported = 0

        while current_date <= end_date:
            logger.info(f"Importing news for {current_date}")

            # Check if news already exists
            if db_service.has_news_for_date(current_date, 'all'):
                logger.info(f"News already exists for {current_date}, skipping")
                current_date += timedelta(days=1)
                continue

            # Scrape news for the date
            target_datetime = datetime.combine(current_date, datetime.min.time())
            news_items = await scraper.scrape_news(target_datetime, analysis_required=False, debug=True)

            if news_items:
                # Store in database
                success = db_service.store_news_items(news_items, current_date, 'all')
                if success:
                    total_imported += len(news_items)
                    logger.info(f"Imported {len(news_items)} news items for {current_date}")
                else:
                    logger.error(f"Failed to store news for {current_date}")
            else:
                logger.info(f"No news found for {current_date}")

            current_date += timedelta(days=1)

        logger.info(f"Bulk import completed. Total imported: {total_imported}")

    except Exception as e:
        logger.error(f"Bulk import failed: {e}")


@app.route('/status', methods=['GET'])
def status():
    """Get application status."""
    try:
        db_healthy = db_service.health_check() if db_service else False
        scheduler_status = digest_scheduler.get_scheduler_status() if digest_scheduler else {'running': False, 'jobs': []}

        # Get user count if database is available
        user_count = 0
        if db_service:
            try:
                users = db_service.get_all_users()
                user_count = len(users)
            except Exception as e:
                logger.error(f"Error getting user count: {e}")

        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "bot": bot is not None,
                "database": db_healthy,
                "digest_scheduler": scheduler_status['running'],
                "webhook": config.telegram_bot_token is not None
            },
            "stats": {
                "users": user_count,
                "scheduler_jobs": len(scheduler_status.get('jobs', []))
            },
            "scheduler": scheduler_status
        })
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/', methods=['GET'])
def home():
    """Home page with basic information."""
    return jsonify({
        "name": "Forex News Telegram Bot",
        "version": "2.0.0",
        "description": "A Telegram bot for delivering Forex news with user preferences and daily digest",
        "endpoints": {
            "/ping": "Health check for Render.com",
            "/health": "Detailed health check",
            "/status": "Application status",
            "/db/stats": "Database statistics",
            "/manual_scrape": "Manual news scraping (POST)",
            "/db/import": "Bulk import news (POST)"
        },
        "features": [
            "User preferences management",
            "Currency filtering",
            "Impact level selection",
            "Daily digest scheduling",
            "AI analysis integration",
            "Database storage and caching"
        ]
    })


@app.route('/add_notification_columns', methods=['POST'])
def add_notification_columns_endpoint():
    """Add notification columns to the database."""
    try:
        if not db_service:
            return jsonify({"error": "Database service not available"}), 500

        # Check if columns already exist
        with db_service.db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))
            existing_columns = [row[0] for row in result]

            if len(existing_columns) == 3:
                return jsonify({
                    "status": "success",
                    "message": "Notification columns already exist",
                    "existing_columns": existing_columns
                })

            # Add missing columns
            columns_added = []

            if 'notifications_enabled' not in existing_columns:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notifications_enabled BOOLEAN DEFAULT FALSE
                """))
                columns_added.append('notifications_enabled')

            if 'notification_minutes' not in existing_columns:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notification_minutes INTEGER DEFAULT 30
                """))
                columns_added.append('notification_minutes')

            if 'notification_impact_levels' not in existing_columns:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN notification_impact_levels TEXT DEFAULT 'high'
                """))
                columns_added.append('notification_impact_levels')

            session.commit()

            return jsonify({
                "status": "success",
                "message": f"Added notification columns: {columns_added}",
                "columns_added": columns_added
            })

    except Exception as e:
        logger.error(f"Error adding notification columns: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/check_notification_columns', methods=['GET'])
def check_notification_columns():
    """Check if notification columns exist in the database."""
    try:
        if not db_service:
            return jsonify({"error": "Database service not available"}), 500

        with db_service.db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))
            existing_columns = [row[0] for row in result]

            return jsonify({
                "status": "success",
                "existing_columns": existing_columns,
                "all_columns_exist": len(existing_columns) == 3,
                "notifications_enabled_exists": 'notifications_enabled' in existing_columns
            })

    except Exception as e:
        logger.error(f"Error checking notification columns: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/test_settings/<int:user_id>', methods=['GET'])
def test_settings(user_id):
    """Test settings for a specific user."""
    try:
        if not db_service:
            return jsonify({"error": "Database service not available"}), 500

        user = db_service.get_or_create_user(user_id)

        # Check notification columns
        with db_service.db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
            """))
            notification_columns = [row[0] for row in result]

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "notification_columns": notification_columns,
            "has_notifications_enabled": hasattr(user, 'notifications_enabled'),
            "has_notification_minutes": hasattr(user, 'notification_minutes'),
            "has_notification_impact_levels": hasattr(user, 'notification_impact_levels'),
            "notifications_enabled_value": getattr(user, 'notifications_enabled', None),
            "notification_minutes_value": getattr(user, 'notification_minutes', None),
            "notification_impact_levels_value": getattr(user, 'notification_impact_levels', None)
        })

    except Exception as e:
        logger.error(f"Error testing settings for user {user_id}: {e}")
        return jsonify({"error": str(e)}), 500


def initialize_application():
    """Initialize the application and start background services."""
    try:
        # Setup webhook if bot is available
        if bot_manager:
            bot_manager.setup_webhook_async()

        logger.info("Application initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")


if __name__ == "__main__":
    initialize_application()
    app.run(host="0.0.0.0", port=10000, debug=False)
