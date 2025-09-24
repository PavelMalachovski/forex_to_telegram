"""Forex news service implementation."""

from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from .base import BaseService
from app.database.models import ForexNewsModel
from app.models.forex_news import ForexNewsCreate, ForexNewsUpdate
from app.core.exceptions import DatabaseError, ValidationError
import structlog

logger = structlog.get_logger(__name__)


class ForexService(BaseService[ForexNewsModel]):
    """Forex news service with business logic."""

    def __init__(self):
        super().__init__(ForexNewsModel)

    async def create_news(self, db: AsyncSession, news_data: ForexNewsCreate) -> ForexNewsModel:
        """Create new forex news."""
        try:
            news_dict = news_data.model_dump()
            return await self.create(db, **news_dict)
        except Exception as e:
            logger.error("Failed to create forex news", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to create forex news: {e}")

    async def get_news_by_date(self, db: AsyncSession, news_date: date) -> List[ForexNewsModel]:
        """Get forex news by date."""
        try:
            start_datetime = datetime.combine(news_date, datetime.min.time())
            end_datetime = datetime.combine(news_date, datetime.max.time())

            result = await db.execute(
                select(ForexNewsModel).where(
                    and_(
                        ForexNewsModel.date >= start_datetime,
                        ForexNewsModel.date <= end_datetime
                    )
                ).order_by(ForexNewsModel.time)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get news by date", date=news_date, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news by date: {e}")

    async def get_news_by_currency(self, db: AsyncSession, currency: str) -> List[ForexNewsModel]:
        """Get forex news by currency."""
        try:
            result = await db.execute(
                select(ForexNewsModel)
                .where(ForexNewsModel.currency == currency)
                .order_by(ForexNewsModel.date.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get news by currency", currency=currency, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news by currency: {e}")

    async def get_news_by_impact_level(self, db: AsyncSession, impact_level: str) -> List[ForexNewsModel]:
        """Get forex news by impact level."""
        try:
            result = await db.execute(
                select(ForexNewsModel)
                .where(ForexNewsModel.impact_level == impact_level)
                .order_by(ForexNewsModel.date.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get news by impact level", impact_level=impact_level, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news by impact level: {e}")

    async def get_upcoming_news(
        self,
        db: AsyncSession,
        hours_ahead: int = 24
    ) -> List[ForexNewsModel]:
        """Get upcoming forex news."""
        try:
            from datetime import timedelta
            now = datetime.utcnow()
            future_time = now + timedelta(hours=hours_ahead)

            result = await db.execute(
                select(ForexNewsModel).where(
                    and_(
                        ForexNewsModel.date >= now,
                        ForexNewsModel.date <= future_time
                    )
                ).order_by(ForexNewsModel.date)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get upcoming news", hours_ahead=hours_ahead, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get upcoming news: {e}")

    async def search_news(
        self,
        db: AsyncSession,
        query: str,
        currency: Optional[str] = None,
        impact_level: Optional[str] = None
    ) -> List[ForexNewsModel]:
        """Search forex news."""
        try:
            search_conditions = [
                or_(
                    ForexNewsModel.event.ilike(f"%{query}%"),
                    ForexNewsModel.analysis.ilike(f"%{query}%")
                )
            ]

            if currency:
                search_conditions.append(ForexNewsModel.currency == currency)

            if impact_level:
                search_conditions.append(ForexNewsModel.impact_level == impact_level)

            result = await db.execute(
                select(ForexNewsModel)
                .where(and_(*search_conditions))
                .order_by(ForexNewsModel.date.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to search news", query=query, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to search news: {e}")

    async def update_news(
        self,
        db: AsyncSession,
        news_id: int,
        news_data: ForexNewsUpdate
    ) -> Optional[ForexNewsModel]:
        """Update forex news."""
        try:
            update_data = news_data.model_dump(exclude_unset=True)
            return await self.update(db, news_id, **update_data)
        except Exception as e:
            logger.error("Failed to update news", news_id=news_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to update news: {e}")

    async def get_news_statistics(self, db: AsyncSession) -> dict:
        """Get forex news statistics."""
        try:
            # Total news count
            total_result = await db.execute(select(ForexNewsModel))
            total_count = len(total_result.scalars().all())

            # News by currency
            currency_result = await db.execute(
                select(ForexNewsModel.currency, db.func.count(ForexNewsModel.id))
                .group_by(ForexNewsModel.currency)
            )
            currency_stats = {row[0]: row[1] for row in currency_result.fetchall()}

            # News by impact level
            impact_result = await db.execute(
                select(ForexNewsModel.impact_level, db.func.count(ForexNewsModel.id))
                .group_by(ForexNewsModel.impact_level)
            )
            impact_stats = {row[0]: row[1] for row in impact_result.fetchall()}

            return {
                "total_count": total_count,
                "by_currency": currency_stats,
                "by_impact_level": impact_stats
            }
        except Exception as e:
            logger.error("Failed to get news statistics", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news statistics: {e}")

    # Additional methods expected by tests
    async def get_forex_news_by_id(self, db: AsyncSession, news_id: int) -> Optional[ForexNewsModel]:
        """Get forex news by ID."""
        try:
            return await self.get_by_id(db, news_id)
        except Exception as e:
            logger.error("Failed to get news by ID", news_id=news_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news by ID: {e}")

    async def get_forex_news_by_date_range(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> List[ForexNewsModel]:
        """Get forex news by date range."""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            result = await db.execute(
                select(ForexNewsModel).where(
                    and_(
                        ForexNewsModel.date >= start_datetime,
                        ForexNewsModel.date <= end_datetime
                    )
                ).order_by(ForexNewsModel.date, ForexNewsModel.time)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get news by date range",
                        start_date=start_date, end_date=end_date, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news by date range: {e}")

    async def get_todays_forex_news(self, db: AsyncSession) -> List[ForexNewsModel]:
        """Get today's forex news."""
        try:
            today = datetime.utcnow().date()
            return await self.get_news_by_date(db, today)
        except Exception as e:
            logger.error("Failed to get today's news", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get today's news: {e}")

    async def get_upcoming_events(self, db: AsyncSession, hours_ahead: int = 24) -> List[ForexNewsModel]:
        """Get upcoming events (alias for get_upcoming_news)."""
        return await self.get_upcoming_news(db, hours_ahead)

    async def update_forex_news(
        self,
        db: AsyncSession,
        news_id: int,
        news_data: ForexNewsUpdate
    ) -> Optional[ForexNewsModel]:
        """Update forex news (alias for update_news)."""
        return await self.update_news(db, news_id, news_data)

    async def delete_forex_news(self, db: AsyncSession, news_id: int) -> bool:
        """Delete forex news."""
        try:
            return await self.delete(db, news_id)
        except Exception as e:
            logger.error("Failed to delete news", news_id=news_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to delete news: {e}")

    async def count_forex_news(self, db: AsyncSession) -> int:
        """Count total forex news."""
        try:
            result = await db.execute(select(func.count(ForexNewsModel.id)))
            return result.scalar() or 0
        except Exception as e:
            logger.error("Failed to count news", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to count news: {e}")

    async def forex_news_exists(self, db: AsyncSession, news_id: int) -> bool:
        """Check if forex news exists."""
        try:
            result = await db.execute(
                select(ForexNewsModel.id).where(ForexNewsModel.id == news_id)
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error("Failed to check news existence", news_id=news_id, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to check news existence: {e}")

    async def get_forex_news_with_filters(
        self,
        db: AsyncSession,
        filters: dict
    ) -> List[ForexNewsModel]:
        """Get forex news with multiple filters."""
        try:
            conditions = []

            if "currency" in filters:
                conditions.append(ForexNewsModel.currency == filters["currency"])

            if "impact_level" in filters:
                conditions.append(ForexNewsModel.impact_level == filters["impact_level"])

            if "date" in filters:
                date_val = filters["date"]
                if isinstance(date_val, date):
                    start_datetime = datetime.combine(date_val, datetime.min.time())
                    end_datetime = datetime.combine(date_val, datetime.max.time())
                    conditions.append(
                        and_(
                            ForexNewsModel.date >= start_datetime,
                            ForexNewsModel.date <= end_datetime
                        )
                    )

            if not conditions:
                # No filters, return all
                result = await db.execute(select(ForexNewsModel).order_by(ForexNewsModel.date.desc()))
            else:
                result = await db.execute(
                    select(ForexNewsModel)
                    .where(and_(*conditions))
                    .order_by(ForexNewsModel.date.desc())
                )

            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get news with filters", filters=filters, error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to get news with filters: {e}")

    async def bulk_create_forex_news(
        self,
        db: AsyncSession,
        news_data_list: List[ForexNewsCreate]
    ) -> List[ForexNewsModel]:
        """Bulk create forex news."""
        try:
            created_news = []
            for news_data in news_data_list:
                news_dict = news_data.model_dump()
                created_news.append(await self.create(db, **news_dict))

            await db.commit()
            return created_news
        except Exception as e:
            await db.rollback()
            logger.error("Failed to bulk create news", error=str(e), exc_info=True)
            raise DatabaseError(f"Failed to bulk create news: {e}")
