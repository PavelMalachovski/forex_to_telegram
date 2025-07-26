from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from .models import DatabaseManager, ForexNews, User

logger = logging.getLogger(__name__)


class ForexNewsService:
    """Service class for handling forex news database operations."""

    def __init__(self, database_url: Optional[str] = None):
        self.db_manager = DatabaseManager(database_url)
        self.db_manager.create_tables()

    # User management methods
    def get_or_create_user(self, telegram_id: int) -> User:
        """Get existing user or create a new one."""
        try:
            with self.db_manager.get_session() as session:
                user = session.query(User).filter(User.telegram_id == telegram_id).first()
                if not user:
                    user = User(telegram_id=telegram_id)
                    session.add(user)
                    session.commit()
                    logger.info(f"Created new user with telegram_id: {telegram_id}")
                return user
        except Exception as e:
            logger.error(f"Error getting/creating user {telegram_id}: {e}")
            raise

    def update_user_preferences(self, telegram_id: int, **kwargs) -> bool:
        """Update user preferences."""
        try:
            with self.db_manager.get_session() as session:
                user = session.query(User).filter(User.telegram_id == telegram_id).first()
                if not user:
                    return False

                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)

                session.commit()
                logger.info(f"Updated preferences for user {telegram_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating user preferences {telegram_id}: {e}")
            return False

    def get_users_for_digest(self, digest_time: datetime.time) -> List[User]:
        """Get all users who should receive digest at the specified time."""
        try:
            with self.db_manager.get_session() as session:
                users = session.query(User).filter(User.digest_time == digest_time).all()
                return users
        except Exception as e:
            logger.error(f"Error getting users for digest at {digest_time}: {e}")
            return []

    def get_all_users(self) -> List[User]:
        """Get all users."""
        try:
            with self.db_manager.get_session() as session:
                users = session.query(User).all()
                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_news_for_date(self, target_date: date, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Get news for a specific date from the database."""
        try:
            with self.db_manager.get_session() as session:
                # Convert date to datetime for comparison
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                query = session.query(ForexNews).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime
                    )
                )

                # Filter by impact level if specified
                if impact_level != "all":
                    query = query.filter(ForexNews.impact_level == impact_level)

                # Order by currency and time
                query = query.order_by(ForexNews.currency, ForexNews.time)

                news_items = query.all()

                # Convert to list of dictionaries
                result = []
                for item in news_items:
                    news_dict = {
                        "time": item.time,
                        "currency": item.currency,
                        "event": item.event,
                        "actual": item.actual or "N/A",
                        "forecast": item.forecast or "N/A",
                        "previous": item.previous or "N/A",
                        "analysis": item.analysis or None,
                        "impact": item.impact_level,  # Add this line for Telegram output
                        "impact_level": item.impact_level,  # Keep for DB/API compatibility
                        "group_analysis": False,  # DB does not store this, set default
                    }
                    result.append(news_dict)

                logger.info(f"Retrieved {len(result)} news items for {target_date} with impact level {impact_level}")
                return result

        except Exception as e:
            logger.error(f"Error retrieving news for date {target_date}: {e}")
            return []

    def has_news_for_date(self, target_date: date, impact_level: str = "high") -> bool:
        """Check if news exists for a specific date."""
        try:
            with self.db_manager.get_session() as session:
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                query = session.query(func.count(ForexNews.id)).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime
                    )
                )

                if impact_level != "all":
                    query = query.filter(ForexNews.impact_level == impact_level)

                count = query.scalar()
                return count > 0

        except Exception as e:
            logger.error(f"Error checking news existence for date {target_date}: {e}")
            return False

    def store_news_items(self, news_items: List[Dict[str, Any]], target_date: date, impact_level: str = "high") -> bool:
        """Store news items in the database."""
        try:
            with self.db_manager.get_session() as session:
                # Delete existing news for this date and impact level
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                session.query(ForexNews).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime,
                        ForexNews.impact_level == impact_level
                    )
                ).delete()

                # Insert new news items
                for item in news_items:
                    news_record = ForexNews(
                        date=target_date,
                        time=item.get("time", "N/A"),
                        currency=item.get("currency", "N/A"),
                        event=item.get("event", "N/A"),
                        actual=item.get("actual", "N/A"),
                        forecast=item.get("forecast", "N/A"),
                        previous=item.get("previous", "N/A"),
                        impact_level=item.get("impact", impact_level),  # Use per-item impact if present
                        analysis=item.get("analysis", None)
                    )
                    session.add(news_record)

                session.commit()
                logger.info(f"Stored {len(news_items)} news items for {target_date} with impact level {impact_level}")
                return True

        except Exception as e:
            logger.error(f"Error storing news for date {target_date}: {e}")
            return False

    def get_date_range_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get statistics for a date range."""
        try:
            with self.db_manager.get_session() as session:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())

                # Get total count
                total_count = session.query(func.count(ForexNews.id)).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime
                    )
                ).scalar()

                # Get count by impact level
                impact_stats = session.query(
                    ForexNews.impact_level,
                    func.count(ForexNews.id)
                ).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime
                    )
                ).group_by(ForexNews.impact_level).all()

                # Get count by currency
                currency_stats = session.query(
                    ForexNews.currency,
                    func.count(ForexNews.id)
                ).filter(
                    and_(
                        ForexNews.date >= start_datetime,
                        ForexNews.date <= end_datetime
                    )
                ).group_by(ForexNews.currency).all()

                return {
                    "total_news": total_count,
                    "impact_levels": dict(impact_stats),
                    "currencies": dict(currency_stats),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }

        except Exception as e:
            logger.error(f"Error getting stats for date range {start_date} to {end_date}: {e}")
            return {}

    def health_check(self) -> bool:
        """Check if the database service is healthy."""
        return self.db_manager.health_check()
