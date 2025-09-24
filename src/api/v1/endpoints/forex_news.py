"""Forex news endpoints."""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database
from src.services.forex_service import ForexService
from src.models.forex_news import ForexNews, ForexNewsCreate, ForexNewsUpdate
from src.core.exceptions import ValidationError, DatabaseError

router = APIRouter()


def get_forex_service() -> ForexService:
    """Get forex service dependency."""
    return ForexService()


@router.post("/", response_model=ForexNews, status_code=status.HTTP_201_CREATED)
async def create_forex_news(
    news_data: ForexNewsCreate,
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Create forex news."""
    try:
        news = await forex_service.create_news(db, news_data)
        return ForexNews.model_validate(news)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[ForexNews])
async def get_forex_news(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    currency: Optional[str] = Query(None),
    impact_level: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Get forex news with filters."""
    try:
        filters = {}
        if currency:
            filters["currency"] = currency
        if impact_level:
            filters["impact_level"] = impact_level

        news_list = await forex_service.get_news(
            db, skip=skip, limit=limit, filters=filters,
            start_date=start_date, end_date=end_date
        )

        return [ForexNews.model_validate(news) for news in news_list]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{news_id}", response_model=ForexNews)
async def get_forex_news_by_id(
    news_id: int,
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Get forex news by ID."""
    news = await forex_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    return ForexNews.model_validate(news)


@router.put("/{news_id}", response_model=ForexNews)
async def update_forex_news(
    news_id: int,
    news_data: ForexNewsUpdate,
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Update forex news."""
    try:
        news = await forex_service.update(db, news_id, **news_data.model_dump(exclude_unset=True))
        if not news:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

        return ForexNews.model_validate(news)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{news_id}")
async def delete_forex_news(
    news_id: int,
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Delete forex news."""
    try:
        success = await forex_service.delete(db, news_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

        return {"message": "News deleted successfully"}
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/today/", response_model=List[ForexNews])
async def get_today_news(
    currency: Optional[str] = Query(None),
    impact_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_database),
    forex_service: ForexService = Depends(get_forex_service),
):
    """Get today's forex news."""
    try:
        news_list = await forex_service.get_today_news(db, currency=currency, impact_level=impact_level)
        return [ForexNews.model_validate(news) for news in news_list]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
