"""Notification service implementation."""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .base import BaseService
from app.database.models import NotificationModel
from app.models.notification import NotificationCreate, NotificationUpdate
from app.core.exceptions import DatabaseError, ValidationError
import structlog

logger = structlog.get_logger(__name__)


class NotificationService(BaseService[NotificationModel]):
    """Notification service with business logic."""

    def __init__(self):
        super().__init__(NotificationModel)

    async def create_notification(self, db: AsyncSession, notification_data: NotificationCreate) -> NotificationModel:
        """Create a new notification."""
        try:
            notification_dict = notification_data.model_dump()
            return await self.create(db, **notification_dict)
        except Exception as e:
            logger.error("Failed to create notification", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to create notification: {e}")

    async def get_pending_notifications(self, db: AsyncSession) -> List[NotificationModel]:
        """Get all pending notifications."""
        try:
            result = await db.execute(
                select(NotificationModel)
                .where(NotificationModel.status == "pending")
                .order_by(NotificationModel.scheduled_time)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get pending notifications", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get pending notifications: {e}")

    async def get_notifications_by_user(self, db: AsyncSession, user_id: int) -> List[NotificationModel]:
        """Get notifications for a specific user."""
        try:
            result = await db.execute(
                select(NotificationModel)
                .where(NotificationModel.user_id == user_id)
                .order_by(NotificationModel.scheduled_time.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get notifications by user", user_id=user_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get notifications by user: {e}")

    async def get_notifications_by_status(self, db: AsyncSession, status: str) -> List[NotificationModel]:
        """Get notifications by status."""
        try:
            result = await db.execute(
                select(NotificationModel)
                .where(NotificationModel.status == status)
                .order_by(NotificationModel.scheduled_time.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get notifications by status", status=status, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get notifications by status: {e}")

    async def get_due_notifications(self, db: AsyncSession) -> List[NotificationModel]:
        """Get notifications that are due to be sent."""
        try:
            now = datetime.utcnow()
            result = await db.execute(
                select(NotificationModel)
                .where(
                    and_(
                        NotificationModel.status == "pending",
                        NotificationModel.scheduled_time <= now
                    )
                )
                .order_by(NotificationModel.scheduled_time)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get due notifications", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get due notifications: {e}")

    async def mark_notification_sent(self, db: AsyncSession, notification_id: int) -> bool:
        """Mark notification as sent."""
        try:
            await db.execute(
                update(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .values(
                    status="sent",
                    sent_at=datetime.utcnow()
                )
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error("Failed to mark notification as sent", notification_id=notification_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to mark notification as sent: {e}")

    async def mark_notification_failed(self, db: AsyncSession, notification_id: int, error_message: str) -> bool:
        """Mark notification as failed."""
        try:
            # Get current retry count
            notification = await self.get(db, notification_id)
            if not notification:
                return False

            new_retry_count = notification.retry_count + 1
            max_retries = 3

            if new_retry_count >= max_retries:
                status = "failed"
            else:
                status = "pending"  # Retry

            await db.execute(
                update(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .values(
                    status=status,
                    error_message=error_message,
                    retry_count=new_retry_count
                )
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error("Failed to mark notification as failed", notification_id=notification_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to mark notification as failed: {e}")

    async def cancel_notification(self, db: AsyncSession, notification_id: int) -> bool:
        """Cancel a notification."""
        try:
            await db.execute(
                update(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .values(status="cancelled")
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error("Failed to cancel notification", notification_id=notification_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to cancel notification: {e}")

    async def create_event_reminder(
        self,
        db: AsyncSession,
        user_id: int,
        event_id: int,
        event_time: datetime,
        minutes_before: int = 30
    ) -> NotificationModel:
        """Create an event reminder notification."""
        try:
            reminder_time = event_time - timedelta(minutes=minutes_before)

            notification_data = NotificationCreate(
                user_id=user_id,
                event_id=event_id,
                notification_type="event_reminder",
                message=f"High impact event starting in {minutes_before} minutes",
                scheduled_time=reminder_time
            )

            return await self.create_notification(db, notification_data)
        except Exception as e:
            logger.error("Failed to create event reminder", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to create event reminder: {e}")

    async def create_digest_notification(
        self,
        db: AsyncSession,
        user_id: int,
        digest_time: datetime
    ) -> NotificationModel:
        """Create a daily digest notification."""
        try:
            notification_data = NotificationCreate(
                user_id=user_id,
                notification_type="digest",
                message="Daily forex news digest",
                scheduled_time=digest_time
            )

            return await self.create_notification(db, notification_data)
        except Exception as e:
            logger.error("Failed to create digest notification", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to create digest notification: {e}")

    async def get_notification_statistics(self, db: AsyncSession) -> dict:
        """Get notification statistics."""
        try:
            # Total notifications
            total_result = await db.execute(select(NotificationModel))
            total_count = len(total_result.scalars().all())

            # Notifications by status
            status_result = await db.execute(
                select(NotificationModel.status, db.func.count(NotificationModel.id))
                .group_by(NotificationModel.status)
            )
            status_stats = {row[0]: row[1] for row in status_result.fetchall()}

            # Notifications by type
            type_result = await db.execute(
                select(NotificationModel.notification_type, db.func.count(NotificationModel.id))
                .group_by(NotificationModel.notification_type)
            )
            type_stats = {row[0]: row[1] for row in type_result.fetchall()}

            return {
                "total_count": total_count,
                "by_status": status_stats,
                "by_type": type_stats
            }
        except Exception as e:
            logger.error("Failed to get notification statistics", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get notification statistics: {e}")
