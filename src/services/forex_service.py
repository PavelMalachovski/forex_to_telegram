"""Forex news service implementation."""

from typing import Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .base import BaseService
from ..database.models import ForexNewsModel
from ..models.forex_news import ForexNews, ForexNewsCreate, ForexNewsUpdate
from ..core.exceptions import DatabaseError, ValidationError


class ForexService(BaseService[ForexNewsModel]):
    """Forex news service with business logic."""

    def __init__(self):
        super().__init__(ForexNewsModel)

    async def create_news(self, db: AsyncSession, news_data: ForexNewsCreate) -> ForexNewsModel:
        """Create forex news."""
        try:
            return await self.create(db, **news_data.model_dump())
        except Exception as e:
            self.logger.error(f"Failed to create forex news: {e}")
            raise DatabaseError(f"Failed to create forex news: {e}")

    async def get_news(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[ForexNewsModel]:
        """Get forex news with filters."""
        try:
            query = select(ForexNewsModel)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(ForexNewsModel, key):
                        query = query.where(getattr(ForexNewsModel, key) == value)

            # Apply date range
            if start_date:
                query = query.where(ForexNewsModel.date >= start_date)
            if end_date:
                query = query.where(ForexNewsModel.date <= end_date)

            query = query.offset(skip).limit(limit).order_by(ForexNewsModel.date.desc())
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get forex news: {e}")
            raise DatabaseError(f"Failed to get forex news: {e}")

    async def get_today_news(
        self,
        db: AsyncSession,
        currency: Optional[str] = None,
        impact_level: Optional[str] = None
    ) -> List[ForexNewsModel]:
        """Get today's forex news."""
        try:
            from datetime import datetime
            today = datetime.now().date()

            query = select(ForexNewsModel).where(ForexNewsModel.date == today)

            if currency:
                query = query.where(ForexNewsModel.currency == currency)
            if impact_level:
                query = query.where(ForexNewsModel.impact_level == impact_level)

            query = query.order_by(ForexNewsModel.time)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get today's forex news: {e}")
            raise DatabaseError(f"Failed to get today's forex news: {e}")

    async def get_news_by_currency(
        self,
        db: AsyncSession,
        currency: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ForexNewsModel]:
        """Get news for a specific currency."""
        try:
            result = await db.execute(
                select(ForexNewsModel)
                .where(ForexNewsModel.currency == currency)
                .offset(skip)
                .limit(limit)
                .order_by(ForexNewsModel.date.desc())
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get news for currency {currency}: {e}")
            raise DatabaseError(f"Failed to get news for currency: {e}")

    async def get_news_by_impact_level(
        self,
        db: AsyncSession,
        impact_level: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ForexNewsModel]:
        """Get news for a specific impact level."""
        try:
            result = await db.execute(
                select(ForexNewsModel)
                .where(ForexNewsModel.impact_level == impact_level)
                .offset(skip)
                .limit(limit)
                .order_by(ForexNewsModel.date.desc())
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get news for impact level {impact_level}: {e}")
            raise DatabaseError(f"Failed to get news for impact level: {e}")
