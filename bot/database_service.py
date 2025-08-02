from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
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
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    user = session.query(User).filter(User.telegram_id == telegram_id).first()
                    if not user:
                        user = User(telegram_id=telegram_id)
                        session.add(user)
                        session.commit()
                        logger.info(f"Created new user with telegram_id: {telegram_id}")
                    return user
                else:
                    # Some columns missing, use raw SQL for getting user
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users WHERE telegram_id = :telegram_id LIMIT 1"

                    result = session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        # User exists, create User object manually
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        user = User()
                        user.id = user_data['id']
                        user.telegram_id = user_data['telegram_id']
                        user.preferred_currencies = user_data['preferred_currencies']
                        user.impact_levels = user_data['impact_levels']
                        user.analysis_required = user_data['analysis_required']
                        user.digest_time = user_data['digest_time']
                        user.created_at = user_data['created_at']
                        user.updated_at = user_data['updated_at']

                        # Set optional fields only if they exist
                        for field in optional_columns:
                            if field in user_data:
                                setattr(user, field, user_data[field])

                        return user
                    else:
                        # User doesn't exist, create new user with raw SQL
                        insert_columns = ['telegram_id', 'created_at', 'updated_at']
                        insert_values = [':telegram_id', 'NOW()', 'NOW()']

                        insert_sql = f"""
                            INSERT INTO users ({', '.join(insert_columns)})
                            VALUES ({', '.join(insert_values)})
                            RETURNING id, telegram_id, preferred_currencies, impact_levels,
                                     analysis_required, digest_time, created_at, updated_at
                        """

                        result = session.execute(text(insert_sql), {'telegram_id': telegram_id})
                        row = result.fetchone()
                        session.commit()

                        # Create User object manually
                        user = User()
                        user.id = row[0]
                        user.telegram_id = row[1]
                        user.preferred_currencies = row[2]
                        user.impact_levels = row[3]
                        user.analysis_required = row[4]
                        user.digest_time = row[5]
                        user.created_at = row[6]
                        user.updated_at = row[7]

                        logger.info(f"Created new user with telegram_id: {telegram_id}")
                        return user

        except Exception as e:
            logger.error(f"Error getting/creating user {telegram_id}: {e}")
            raise

    def update_user_preferences(self, telegram_id: int, **kwargs) -> bool:
        """Update user preferences."""
        try:
            with self.db_manager.get_session() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    user = session.query(User).filter(User.telegram_id == telegram_id).first()
                    if not user:
                        return False

                    for key, value in kwargs.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                        else:
                            # Handle optional fields that might not exist in database yet
                            if key in required_columns:
                                # Skip updating these fields if they don't exist in the database
                                continue

                    session.commit()
                    logger.info(f"Updated preferences for user {telegram_id}")
                    return True
                else:
                    # Some columns missing, use raw SQL
                    # First get the user to check if it exists
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users WHERE telegram_id = :telegram_id LIMIT 1"

                    result = session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if not row:
                        return False

                    # Build UPDATE statement with only existing columns
                    update_parts = []
                    update_values = {'telegram_id': telegram_id}

                    for key, value in kwargs.items():
                        if key in columns:
                            update_parts.append(f"{key} = :{key}")
                            update_values[key] = value
                        elif key in ['notifications_enabled', 'notification_minutes', 'notification_impact_levels', 'timezone', 'charts_enabled', 'chart_type', 'chart_window_hours']:
                            # Skip notification and chart fields that don't exist
                            continue

                    if update_parts:
                        update_sql = f"""
                            UPDATE users
                            SET {', '.join(update_parts)}, updated_at = NOW()
                            WHERE telegram_id = :telegram_id
                        """

                        session.execute(text(update_sql), update_values)
                        session.commit()
                        logger.info(f"Updated preferences for user {telegram_id}")
                        return True
                    else:
                        logger.info(f"No valid fields to update for user {telegram_id}")
                        return True

        except Exception as e:
            logger.error(f"Error updating user preferences {telegram_id}: {e}")
            return False

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        try:
            with self.db_manager.get_session() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    return session.query(User).filter(User.telegram_id == telegram_id).first()
                else:
                    # Some columns missing, use raw SQL
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users WHERE telegram_id = :telegram_id LIMIT 1"

                    result = session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = User()
                        user.id = user_data['id']
                        user.telegram_id = user_data['telegram_id']
                        user.preferred_currencies = user_data['preferred_currencies']
                        user.impact_levels = user_data['impact_levels']
                        user.analysis_required = user_data['analysis_required']
                        user.digest_time = user_data['digest_time']
                        user.created_at = user_data['created_at']
                        user.updated_at = user_data['updated_at']

                        # Set notification fields only if they exist
                        if 'notifications_enabled' in user_data:
                            user.notifications_enabled = user_data['notifications_enabled']
                        if 'notification_minutes' in user_data:
                            user.notification_minutes = user_data['notification_minutes']
                        if 'notification_impact_levels' in user_data:
                            user.notification_impact_levels = user_data['notification_impact_levels']

                        return user

                return None
        except Exception as e:
            logger.error(f"Error getting user by telegram ID {telegram_id}: {e}")
            return None

    def get_user_preferences(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences by telegram ID."""
        try:
            with self.db_manager.get_session() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    user = session.query(User).filter(User.telegram_id == telegram_id).first()
                    if user:
                        return user.to_dict()
                else:
                    # Some columns missing, use raw SQL
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users WHERE telegram_id = :telegram_id LIMIT 1"

                    result = session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = User()
                        user.id = user_data['id']
                        user.telegram_id = user_data['telegram_id']
                        user.preferred_currencies = user_data['preferred_currencies']
                        user.impact_levels = user_data['impact_levels']
                        user.analysis_required = user_data['analysis_required']
                        user.digest_time = user_data['digest_time']
                        user.created_at = user_data['created_at']
                        user.updated_at = user_data['updated_at']

                        # Set optional fields only if they exist
                        for field in optional_columns:
                            if field in user_data:
                                setattr(user, field, user_data[field])

                        return user.to_dict()

                return None
        except Exception as e:
            logger.error(f"Error getting user preferences for {telegram_id}: {e}")
            return None

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
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    users = session.query(User).all()
                else:
                    # Some columns missing, use raw SQL
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users"

                    result = session.execute(text(sql))
                    users = []
                    for row in result:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = User()
                        user.id = user_data['id']
                        user.telegram_id = user_data['telegram_id']
                        user.preferred_currencies = user_data['preferred_currencies']
                        user.impact_levels = user_data['impact_levels']
                        user.analysis_required = user_data['analysis_required']
                        user.digest_time = user_data['digest_time']
                        user.created_at = user_data['created_at']
                        user.updated_at = user_data['updated_at']

                        # Set optional fields only if they exist
                        for field in optional_columns:
                            if field in user_data:
                                setattr(user, field, user_data[field])

                        users.append(user)

                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_users_with_notifications_enabled(self) -> List[User]:
        """Get all users who have notifications enabled."""
        try:
            with self.db_manager.get_session() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name IN (
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    )
                """))
                all_columns = [row[0] for row in result]

                if 'notifications_enabled' not in all_columns:
                    # Notification columns don't exist, return empty list
                    logger.info("Notification columns not found, returning empty list")
                    return []

                # Check if we have all required columns
                required_columns = [
                    'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                    'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                ]

                if all(col in all_columns for col in required_columns):
                    # All required columns exist, use normal query
                    users = session.query(User).filter(User.notifications_enabled == True).all()
                else:
                    # Some columns missing, use raw SQL
                    base_columns = ['id', 'telegram_id', 'preferred_currencies', 'impact_levels',
                                  'analysis_required', 'digest_time', 'created_at', 'updated_at']

                    # Add optional columns only if they exist
                    optional_columns = [
                        'notifications_enabled', 'notification_minutes', 'notification_impact_levels',
                        'charts_enabled', 'chart_type', 'chart_window_hours', 'timezone'
                    ]

                    columns = base_columns.copy()
                    for col in optional_columns:
                        if col in all_columns:
                            columns.append(col)

                    columns_str = ', '.join([f'users.{col} AS users_{col}' for col in columns])
                    sql = f"SELECT {columns_str} FROM users WHERE notifications_enabled = TRUE"

                    result = session.execute(text(sql))
                    users = []
                    for row in result:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = User()
                        user.id = user_data['id']
                        user.telegram_id = user_data['telegram_id']
                        user.preferred_currencies = user_data['preferred_currencies']
                        user.impact_levels = user_data['impact_levels']
                        user.analysis_required = user_data['analysis_required']
                        user.digest_time = user_data['digest_time']
                        user.created_at = user_data['created_at']
                        user.updated_at = user_data['updated_at']

                        # Set optional fields only if they exist
                        for field in optional_columns:
                            if field in user_data:
                                setattr(user, field, user_data[field])

                        users.append(user)

                return users
        except Exception as e:
            logger.error(f"Error getting users with notifications enabled: {e}")
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
