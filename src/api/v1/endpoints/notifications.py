"""Notification endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database
from src.services.notification_service import NotificationService
from src.models.notification import Notification, NotificationCreate
from src.core.exceptions import ValidationError, DatabaseError

router = APIRouter()


def get_notification_service() -> NotificationService:
    """Get notification service dependency."""
    return NotificationService()


@router.post("/", response_model=Notification, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Create a notification."""
    try:
        notification = await notification_service.create_notification(db, notification_data)
        return Notification.model_validate(notification)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[Notification])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    notification_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Get notifications with filters."""
    try:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if status:
            filters["status"] = status
        if notification_type:
            filters["notification_type"] = notification_type

        notifications = await notification_service.get_notifications(db, skip=skip, limit=limit, filters=filters)
        return [Notification.model_validate(notification) for notification in notifications]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{notification_id}", response_model=Notification)
async def get_notification_by_id(
    notification_id: int,
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Get notification by ID."""
    notification = await notification_service.get_by_id(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return Notification.model_validate(notification)


@router.get("/pending/", response_model=List[Notification])
async def get_pending_notifications(
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Get pending notifications."""
    try:
        notifications = await notification_service.get_pending_notifications(db)
        return [Notification.model_validate(notification) for notification in notifications]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{notification_id}/mark-sent")
async def mark_notification_sent(
    notification_id: int,
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Mark notification as sent."""
    try:
        success = await notification_service.mark_sent(db, notification_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        return {"message": "Notification marked as sent"}
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{notification_id}/mark-failed")
async def mark_notification_failed(
    notification_id: int,
    error_message: str,
    db: AsyncSession = Depends(get_database),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Mark notification as failed."""
    try:
        success = await notification_service.mark_failed(db, notification_id, error_message)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        return {"message": "Notification marked as failed"}
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
