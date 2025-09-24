"""Telegram webhook endpoints."""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database
from src.services.telegram_service import TelegramService
from src.models.telegram import TelegramUpdate
from src.core.exceptions import TelegramError, ValidationError

router = APIRouter()


def get_telegram_service() -> TelegramService:
    """Get telegram service dependency."""
    return TelegramService()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    update_data: TelegramUpdate,
    db: AsyncSession = Depends(get_database),
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """Handle Telegram webhook updates."""
    try:
        # Process the update
        await telegram_service.process_update(db, update_data)

        return {"status": "ok"}

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/webhook/info")
async def webhook_info(
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """Get webhook information."""
    try:
        info = await telegram_service.get_webhook_info()
        return info
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/webhook/set")
async def set_webhook(
    url: str,
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """Set webhook URL."""
    try:
        result = await telegram_service.set_webhook(url)
        return result
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/webhook")
async def delete_webhook(
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """Delete webhook."""
    try:
        result = await telegram_service.delete_webhook()
        return result
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
