"""Base service class with common functionality."""

from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

from ..core.logging import LoggerMixin
from ..core.exceptions import DatabaseError

T = TypeVar("T", bound=DeclarativeBase)


class BaseService(Generic[T], LoggerMixin):
    """Base service class with common CRUD operations."""

    def __init__(self, model: type[T]):
        self.model = model

    async def create(self, db: AsyncSession, **kwargs) -> T:
        """Create a new record."""
        try:
            instance = self.model(**kwargs)
            db.add(instance)
            await db.flush()
            await db.refresh(instance)
            return instance
        except Exception as e:
            self.logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to create {self.model.__name__}: {e}")

    async def get_by_id(self, db: AsyncSession, id: int) -> Optional[T]:
        """Get record by ID."""
        try:
            result = await db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} by ID {id}: {e}")
            raise DatabaseError(f"Failed to get {self.model.__name__} by ID: {e}")

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get all records with pagination and filters."""
        try:
            query = select(self.model)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} records: {e}")
            raise DatabaseError(f"Failed to get {self.model.__name__} records: {e}")

    async def update(self, db: AsyncSession, id: int, **kwargs) -> Optional[T]:
        """Update record by ID."""
        try:
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}

            if not update_data:
                return await self.get_by_id(db, id)

            await db.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**update_data)
            )
            await db.flush()
            return await self.get_by_id(db, id)
        except Exception as e:
            self.logger.error(f"Failed to update {self.model.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to update {self.model.__name__}: {e}")

    async def delete(self, db: AsyncSession, id: int) -> bool:
        """Delete record by ID."""
        try:
            result = await db.execute(
                delete(self.model).where(self.model.id == id)
            )
            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to delete {self.model.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to delete {self.model.__name__}: {e}")

    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters."""
        try:
            query = select(self.model)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            result = await db.execute(query)
            return len(result.scalars().all())
        except Exception as e:
            self.logger.error(f"Failed to count {self.model.__name__} records: {e}")
            raise DatabaseError(f"Failed to count {self.model.__name__} records: {e}")
