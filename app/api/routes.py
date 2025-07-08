
"""
Flask API routes.
"""

from datetime import datetime, date
from flask import Flask, request, jsonify
from sqlalchemy.orm import Session
import telebot

from app.config import config
from app.database import get_db
from app.services import NewsService
from app.scheduler import TaskScheduler
import logging

logger = logging.getLogger(__name__)

def create_api_routes(app: Flask, bot: telebot.TeleBot, scheduler: TaskScheduler):
    """
    Create and register API routes.
    
    Args:
        app: Flask application instance
        bot: Telegram bot instance
        scheduler: Task scheduler instance
    """
    
    @app.route('/', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'ok',
            'message': 'Forex Bot is running',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.route('/ping', methods=['GET'])
    def ping():
        """Ping endpoint for keeping the service alive."""
        return jsonify({
            'status': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Telegram webhook endpoint."""
        if not bot:
            logger.error("Bot not initialized")
            return jsonify({'error': 'Bot not configured'}), 500
        
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return jsonify({'status': 'ok'})
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({'error': 'Webhook processing failed'}), 500
    
    @app.route('/run', methods=['GET'])
    def manual_scraping():
        """Manual scraping endpoint."""
        try:
            # Get parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            api_key = request.args.get('api_key')
            
            # Validate API key
            if not api_key or api_key != config.API_KEY:
                return jsonify({'error': 'Invalid or missing API key'}), 401
            
            # Parse dates
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                else:
                    start_date = date.today()
                
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                else:
                    end_date = start_date
                    
            except ValueError as e:
                return jsonify({'error': f'Invalid date format: {e}'}), 400
            
            # Validate date range
            if start_date > end_date:
                return jsonify({'error': 'Start date must be before or equal to end date'}), 400
            
            # Run scraping
            result = scheduler.run_manual_scraping(start_date, end_date)
            
            return jsonify({
                'message': 'Manual scraping completed',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Manual scraping endpoint error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/news', methods=['GET'])
    def get_news():
        """Get news events endpoint."""
        try:
            # Get parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            impact_levels = request.args.getlist('impact_level')
            currencies = request.args.getlist('currency')
            
            # Parse dates
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                else:
                    start_date = date.today()
                
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                else:
                    end_date = start_date
                    
            except ValueError as e:
                return jsonify({'error': f'Invalid date format: {e}'}), 400
            
            # Get news from database
            db: Session = next(get_db())
            try:
                news_service = NewsService(db)
                news_events = news_service.get_news_by_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    impact_levels=impact_levels if impact_levels else None,
                    currencies=currencies if currencies else None
                )
                
                # Convert to JSON-serializable format
                events_data = []
                for event in news_events:
                    events_data.append({
                        'id': event.id,
                        'date': event.event_date.isoformat(),
                        'time': event.event_time.strftime('%H:%M'),
                        'currency': event.currency.code,
                        'event_name': event.event_name,
                        'forecast': event.forecast,
                        'previous_value': event.previous_value,
                        'actual_value': event.actual_value,
                        'impact_level': event.impact_level.code,
                        'analysis': event.analysis,
                        'source_url': event.source_url,
                        'scraped_at': event.scraped_at.isoformat() if event.scraped_at else None
                    })
                
                return jsonify({
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'count': len(events_data),
                    'events': events_data
                })
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Get news endpoint error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/stats', methods=['GET'])
    def get_stats():
        """Get statistics endpoint."""
        try:
            db: Session = next(get_db())
            try:
                # Get basic statistics
                from app.database.models import NewsEvent, ScrapingLog
                from sqlalchemy import func
                
                # Count total events
                total_events = db.query(func.count(NewsEvent.id)).scalar()
                
                # Count events by impact level
                impact_stats = db.query(
                    NewsEvent.impact_level_id,
                    func.count(NewsEvent.id)
                ).group_by(NewsEvent.impact_level_id).all()
                
                # Get recent scraping logs
                recent_logs = db.query(ScrapingLog).order_by(
                    ScrapingLog.created_at.desc()
                ).limit(5).all()
                
                logs_data = []
                for log in recent_logs:
                    logs_data.append({
                        'date': log.created_at.isoformat(),
                        'start_date': log.start_date.isoformat(),
                        'end_date': log.end_date.isoformat(),
                        'events_scraped': log.events_scraped,
                        'status': log.status,
                        'duration_seconds': log.duration_seconds
                    })
                
                return jsonify({
                    'total_events': total_events,
                    'impact_stats': dict(impact_stats),
                    'recent_scraping_logs': logs_data
                })
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Get stats endpoint error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
