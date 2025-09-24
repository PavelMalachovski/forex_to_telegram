"""Advanced database service with schema evolution handling for Render.com PostgreSQL."""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
import structlog

from app.database.connection import db_manager
from app.database.models import UserModel, ForexNewsModel

logger = structlog.get_logger(__name__)


class DatabaseService:
    """Advanced database service with schema evolution handling."""

    def __init__(self):
        self.db_manager = db_manager

    async def get_or_create_user(self, telegram_id: int) -> UserModel:
        """Get existing user or create a new one with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    user = await session.get(UserModel, telegram_id)
                    if not user:
                        user = UserModel(telegram_id=telegram_id)
                        session.add(user)
                        await session.commit()
                        logger.info("Created new user", telegram_id=telegram_id)
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

                    result = await session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        # User exists, create User object manually
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        user = UserModel()
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

                        result = await session.execute(text(insert_sql), {'telegram_id': telegram_id})
                        row = result.fetchone()
                        await session.commit()

                        # Create User object manually
                        user = UserModel()
                        user.id = row[0]
                        user.telegram_id = row[1]
                        user.preferred_currencies = row[2]
                        user.impact_levels = row[3]
                        user.analysis_required = row[4]
                        user.digest_time = row[5]
                        user.created_at = row[6]
                        user.updated_at = row[7]

                        logger.info("Created new user", telegram_id=telegram_id)
                        return user

        except Exception as e:
            logger.error("Error getting/creating user", telegram_id=telegram_id, error=str(e))
            raise

    async def update_user_preferences(self, telegram_id: int, **kwargs) -> bool:
        """Update user preferences with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    user = await session.get(UserModel, telegram_id)
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

                    await session.commit()
                    logger.info("Updated preferences for user", telegram_id=telegram_id)
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

                    result = await session.execute(text(sql), {'telegram_id': telegram_id})
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

                        await session.execute(text(update_sql), update_values)
                        await session.commit()
                        logger.info("Updated preferences for user", telegram_id=telegram_id)
                        return True
                    else:
                        logger.info("No valid fields to update for user", telegram_id=telegram_id)
                        return True

        except Exception as e:
            logger.error("Error updating user preferences", telegram_id=telegram_id, error=str(e))
            return False

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserModel]:
        """Get user by telegram ID with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    return await session.get(UserModel, telegram_id)
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

                    result = await session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = UserModel()
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
            logger.error("Error getting user by telegram ID", telegram_id=telegram_id, error=str(e))
            return None

    async def get_user_preferences(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences by telegram ID with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    user = await session.get(UserModel, telegram_id)
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

                    result = await session.execute(text(sql), {'telegram_id': telegram_id})
                    row = result.fetchone()

                    if row:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = UserModel()
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
            logger.error("Error getting user preferences", telegram_id=telegram_id, error=str(e))
            return None

    async def get_users_for_digest(self, digest_time: datetime.time) -> List[UserModel]:
        """Get all users who should receive digest at the specified time."""
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    text("SELECT * FROM users WHERE digest_time = :digest_time"),
                    {'digest_time': digest_time}
                )
                users = []
                for row in result:
                    user = UserModel()
                    # Map row data to user object
                    # This is a simplified version - in practice you'd map all fields
                    user.id = row[0]
                    user.telegram_id = row[1]
                    # ... map other fields
                    users.append(user)
                return users
        except Exception as e:
            logger.error("Error getting users for digest", digest_time=digest_time, error=str(e))
            return []

    async def get_all_users(self) -> List[UserModel]:
        """Get all users with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    result = await session.execute(text("SELECT * FROM users"))
                    users = []
                    for row in result:
                        user = UserModel()
                        # Map row data to user object
                        # This is a simplified version - in practice you'd map all fields
                        user.id = row[0]
                        user.telegram_id = row[1]
                        # ... map other fields
                        users.append(user)
                    return users
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

                    result = await session.execute(text(sql))
                    users = []
                    for row in result:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = UserModel()
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
            logger.error("Error getting all users", error=str(e))
            return []

    async def get_users_with_notifications_enabled(self) -> List[UserModel]:
        """Get all users who have notifications enabled with schema evolution handling."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Check if all required columns exist (notification + chart + timezone)
                result = await session.execute(text("""
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
                    result = await session.execute(text("SELECT * FROM users WHERE notifications_enabled = TRUE"))
                    users = []
                    for row in result:
                        user = UserModel()
                        # Map row data to user object
                        # This is a simplified version - in practice you'd map all fields
                        user.id = row[0]
                        user.telegram_id = row[1]
                        # ... map other fields
                        users.append(user)
                    return users
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

                    result = await session.execute(text(sql))
                    users = []
                    for row in result:
                        user_data = {}
                        for i, col in enumerate(columns):
                            user_data[col] = row[i]

                        # Create User object manually
                        user = UserModel()
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
            logger.error("Error getting users with notifications enabled", error=str(e))
            return []

    async def get_news_for_date(self, target_date: date, impact_level: str = "high") -> List[Dict[str, Any]]:
        """Get news for a specific date from the database."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Convert date to datetime for comparison
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                query_sql = """
                    SELECT * FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                """
                params = {'start_datetime': start_datetime, 'end_datetime': end_datetime}

                # Filter by impact level if specified
                if impact_level != "all":
                    query_sql += " AND impact_level = :impact_level"
                    params['impact_level'] = impact_level

                # Order by currency and time
                query_sql += " ORDER BY currency, time"

                result = await session.execute(text(query_sql), params)
                news_items = result.fetchall()

                # Convert to list of dictionaries
                result_list = []
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
                    result_list.append(news_dict)

                logger.info("Retrieved news items", count=len(result_list), date=target_date, impact_level=impact_level)
                return result_list

        except Exception as e:
            logger.error("Error retrieving news for date", date=target_date, error=str(e))
            return []

    async def has_news_for_date(self, target_date: date, impact_level: str = "high") -> bool:
        """Check if news exists for a specific date."""
        try:
            async with self.db_manager.get_session_async() as session:
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                query_sql = """
                    SELECT COUNT(*) FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                """
                params = {'start_datetime': start_datetime, 'end_datetime': end_datetime}

                if impact_level != "all":
                    query_sql += " AND impact_level = :impact_level"
                    params['impact_level'] = impact_level

                result = await session.execute(text(query_sql), params)
                count = result.scalar()
                return count > 0

        except Exception as e:
            logger.error("Error checking news existence for date", date=target_date, error=str(e))
            return False

    async def store_news_items(self, news_items: List[Dict[str, Any]], target_date: date, impact_level: str = "high") -> bool:
        """Store news items in the database."""
        try:
            async with self.db_manager.get_session_async() as session:
                # Delete existing news for this date. If impact_level == 'all', remove all rows for the date
                # to avoid duplicates across repeated imports.
                start_datetime = datetime.combine(target_date, datetime.min.time())
                end_datetime = datetime.combine(target_date, datetime.max.time())

                delete_sql = """
                    DELETE FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                """
                params = {'start_datetime': start_datetime, 'end_datetime': end_datetime}

                if impact_level != "all":
                    delete_sql += " AND impact_level = :impact_level"
                    params['impact_level'] = impact_level

                await session.execute(text(delete_sql), params)

                # Insert new news items
                for item in news_items:
                    insert_sql = """
                        INSERT INTO forex_news (date, time, currency, event, actual, forecast, previous, impact_level, analysis)
                        VALUES (:date, :time, :currency, :event, :actual, :forecast, :previous, :impact_level, :analysis)
                    """
                    await session.execute(text(insert_sql), {
                        'date': target_date,
                        'time': item.get("time", "N/A"),
                        'currency': item.get("currency", "N/A"),
                        'event': item.get("event", "N/A"),
                        'actual': item.get("actual", "N/A"),
                        'forecast': item.get("forecast", "N/A"),
                        'previous': item.get("previous", "N/A"),
                        'impact_level': item.get("impact", impact_level),  # Use per-item impact if present
                        'analysis': item.get("analysis", None)
                    })

                await session.commit()
                logger.info("Stored news items", count=len(news_items), date=target_date, impact_level=impact_level)
                return True

        except Exception as e:
            logger.error("Error storing news for date", date=target_date, error=str(e))
            return False

    async def get_date_range_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get statistics for a date range."""
        try:
            async with self.db_manager.get_session_async() as session:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())

                # Get total count
                total_count_sql = """
                    SELECT COUNT(*) FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                """
                result = await session.execute(text(total_count_sql), {'start_datetime': start_datetime, 'end_datetime': end_datetime})
                total_count = result.scalar()

                # Get count by impact level
                impact_stats_sql = """
                    SELECT impact_level, COUNT(*)
                    FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                    GROUP BY impact_level
                """
                result = await session.execute(text(impact_stats_sql), {'start_datetime': start_datetime, 'end_datetime': end_datetime})
                impact_stats = dict(result.fetchall())

                # Get count by currency
                currency_stats_sql = """
                    SELECT currency, COUNT(*)
                    FROM forex_news
                    WHERE date >= :start_datetime AND date <= :end_datetime
                    GROUP BY currency
                """
                result = await session.execute(text(currency_stats_sql), {'start_datetime': start_datetime, 'end_datetime': end_datetime})
                currency_stats = dict(result.fetchall())

                return {
                    "total_news": total_count,
                    "impact_levels": impact_stats,
                    "currencies": currency_stats,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }

        except Exception as e:
            logger.error("Error getting stats for date range", start_date=start_date, end_date=end_date, error=str(e))
            return {}

    async def health_check(self) -> bool:
        """Check if the database service is healthy."""
        try:
            async with self.db_manager.get_session_async() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
