"""User service implementation."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from .base import BaseService
from ..database.models import UserModel
from ..models.user import User, UserCreate, UserUpdate, UserPreferences
from ..core.exceptions import DatabaseError, ValidationError


class UserService(BaseService[UserModel]):
    """User service with business logic."""

    def __init__(self):
        super().__init__(UserModel)

    async def get_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[UserModel]:
        """Get user by Telegram ID."""
        try:
            result = await db.execute(
                select(UserModel).where(UserModel.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get user by Telegram ID {telegram_id}: {e}")
            raise DatabaseError(f"Failed to get user by Telegram ID: {e}")

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> UserModel:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = await self.get_by_telegram_id(db, user_data.telegram_id)
            if existing_user:
                raise ValidationError(f"User with Telegram ID {user_data.telegram_id} already exists")

            # Create user
            user_dict = user_data.model_dump()
            preferences = user_dict.pop("preferences", {})

            # Convert preferences to individual fields
            user_dict.update(preferences)

            return await self.create(db, **user_dict)
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            raise DatabaseError(f"Failed to create user: {e}")

    async def update_user(self, db: AsyncSession, telegram_id: int, user_data: UserUpdate) -> Optional[UserModel]:
        """Update user by Telegram ID."""
        try:
            user = await self.get_by_telegram_id(db, telegram_id)
            if not user:
                return None

            update_dict = user_data.model_dump(exclude_unset=True)

            # Handle preferences update
            if "preferences" in update_dict:
                preferences = update_dict.pop("preferences")
                update_dict.update(preferences.model_dump())

            return await self.update(db, user.id, **update_dict)
        except Exception as e:
            self.logger.error(f"Failed to update user {telegram_id}: {e}")
            raise DatabaseError(f"Failed to update user: {e}")

    async def update_preferences(self, db: AsyncSession, telegram_id: int, preferences: UserPreferences) -> Optional[UserModel]:
        """Update user preferences."""
        try:
            user = await self.get_by_telegram_id(db, telegram_id)
            if not user:
                return None

            preferences_dict = preferences.model_dump()
            return await self.update(db, user.id, **preferences_dict)
        except Exception as e:
            self.logger.error(f"Failed to update preferences for user {telegram_id}: {e}")
            raise DatabaseError(f"Failed to update preferences: {e}")

    async def get_active_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """Get active users."""
        try:
            result = await db.execute(
                select(UserModel)
                .where(UserModel.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get active users: {e}")
            raise DatabaseError(f"Failed to get active users: {e}")

    async def get_users_by_currency(self, db: AsyncSession, currency: str) -> List[UserModel]:
        """Get users who have a specific currency in their preferences."""
        try:
            result = await db.execute(
                select(UserModel).where(
                    UserModel.preferred_currencies.contains([currency])
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get users by currency {currency}: {e}")
            raise DatabaseError(f"Failed to get users by currency: {e}")

    async def get_users_by_impact_level(self, db: AsyncSession, impact_level: str) -> List[UserModel]:
        """Get users who have a specific impact level in their preferences."""
        try:
            result = await db.execute(
                select(UserModel).where(
                    UserModel.impact_levels.contains([impact_level])
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get users by impact level {impact_level}: {e}")
            raise DatabaseError(f"Failed to get users by impact level: {e}")

    async def update_last_active(self, db: AsyncSession, telegram_id: int) -> None:
        """Update user's last active timestamp."""
        try:
            from datetime import datetime
            await db.execute(
                update(UserModel)
                .where(UserModel.telegram_id == telegram_id)
                .values(last_active=datetime.utcnow())
            )
            await db.flush()
        except Exception as e:
            self.logger.error(f"Failed to update last active for user {telegram_id}: {e}")
            raise DatabaseError(f"Failed to update last active: {e}")
