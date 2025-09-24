"""Notification service implementation."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .base import BaseService
from ..database.models import NotificationModel
from ..models.notification import Notification, NotificationCreate
from ..core.exceptions import DatabaseError, ValidationError


class NotificationService(BaseService[NotificationModel]):
    """Notification service with business logic."""

    def __init__(self):
        super().__init__(NotificationModel)

    async def create_notification(self, db: AsyncSession, notification_data: NotificationCreate) -> NotificationModel:
        """Create a notification."""
        try:
            return await self.create(db, **notification_data.model_dump())
        except Exception as e:
            self.logger.error(f"Failed to create notification: {e}")
            raise DatabaseError(f"Failed to create notification: {e}")

    async def get_notifications(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict] = None
    ) -> List[NotificationModel]:
        """Get notifications with filters."""
        try:
            query = select(NotificationModel)

            if filters:
                for key, value in filters.items():
                    if hasattr(NotificationModel, key):
                        query = query.where(getattr(NotificationModel, key) == value)

            query = query.offset(skip).limit(limit).order_by(NotificationModel.scheduled_time.desc())
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get notifications: {e}")
            raise DatabaseError(f"Failed to get notifications: {e}")

    async def get_pending_notifications(self, db: AsyncSession) -> List[NotificationModel]:
        """Get pending notifications."""
        try:
            result = await db.execute(
                select(NotificationModel)
                .where(NotificationModel.status == "pending")
                .order_by(NotificationModel.scheduled_time)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get pending notifications: {e}")
            raise DatabaseError(f"Failed to get pending notifications: {e}")

    async def mark_sent(self, db: AsyncSession, notification_id: int) -> bool:
        """Mark notification as sent."""
        try:
            from datetime import datetime
            success = await self.update(
                db,
                notification_id,
                status="sent",
                sent_at=datetime.utcnow()
            )
            return success is not None
        except Exception as e:
            self.logger.error(f"Failed to mark notification {notification_id} as sent: {e}")
            raise DatabaseError(f"Failed to mark notification as sent: {e}")

    async def mark_failed(self, db: AsyncSession, notification_id: int, error_message: str) -> bool:
        """Mark notification as failed."""
        try:
            success = await self.update(
                db,
                notification_id,
                status="failed",
                error_message=error_message
            )
            return success is not None
        except Exception as e:
            self.logger.error(f"Failed to mark notification {notification_id} as failed: {e}")
            raise DatabaseError(f"Failed to mark notification as failed: {e}")
