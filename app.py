#!/usr/bin/env python3
"""Forex News Telegram Bot (modular version)."""

import asyncio
from datetime import datetime

from flask import Flask, request, jsonify
import telebot

from bot.config import Config, setup_logging
from bot.telegram_handlers import TelegramBotManager, RenderKeepAlive, register_handlers
from bot.scraper import ChatGPTAnalyzer, ForexNewsScraper, process_forex_news

config = Config()
logger = setup_logging()
app = Flask(__name__)

bot_manager = TelegramBotManager(config)
bot = bot_manager.bot

keep_alive = RenderKeepAlive(config)

analyzer = ChatGPTAnalyzer(config.openai_api_key)
scraper = ForexNewsScraper(config, analyzer)

if bot:
    register_handlers(bot, lambda date, impact, debug: process_forex_news(scraper, bot, config, date, impact, debug), config)


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
    result = asyncio.run(process_forex_news(scraper, bot, config, target_date, impact_level, debug))
    return jsonify({
        "status": "success",
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "impact_level": impact_level,
        "news_count": len(result),
        "news_items": result if debug else "News sent to Telegram",
    })


@app.route('/status', methods=['GET'])
def status():
    missing_vars = config.validate_required_vars()
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
        },
    })


def initialize_application():
    logger.info("Starting Forex News Telegram Bot...")
    missing_vars = config.validate_required_vars()
    if missing_vars:
        logger.warning("Missing environment variables: %s", missing_vars)
    if bot and config.render_hostname:
        bot_manager.setup_webhook_async()
    else:
        logger.warning("Webhook setup skipped: Bot or hostname not configured")
    logger.info("Application initialized successfully on port %s", config.port)


if __name__ == '__main__':
    initialize_application()
    app.run(host='0.0.0.0', port=config.port, debug=False, threaded=True)
