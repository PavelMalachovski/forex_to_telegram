"""User endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_database
from src.services.user_service import UserService
from src.models.user import User, UserCreate, UserUpdate, UserPreferences
from src.core.exceptions import ValidationError, DatabaseError

router = APIRouter()


def get_user_service() -> UserService:
    """Get user service dependency."""
    return UserService()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Create a new user."""
    try:
        user = await user_service.create_user(db, user_data)
        return User.model_validate(user)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{telegram_id}", response_model=User)
async def get_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Get user by Telegram ID."""
    user = await user_service.get_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return User.model_validate(user)


@router.put("/{telegram_id}", response_model=User)
async def update_user(
    telegram_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Update user by Telegram ID."""
    try:
        user = await user_service.update_user(db, telegram_id, user_data)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return User.model_validate(user)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{telegram_id}/preferences", response_model=User)
async def update_user_preferences(
    telegram_id: int,
    preferences: UserPreferences,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Update user preferences."""
    try:
        user = await user_service.update_preferences(db, telegram_id, preferences)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return User.model_validate(user)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Get users with pagination."""
    try:
        if active_only:
            users = await user_service.get_active_users(db, skip, limit)
        else:
            users = await user_service.get_all(db, skip, limit)

        return [User.model_validate(user) for user in users]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/by-currency/{currency}", response_model=List[User])
async def get_users_by_currency(
    currency: str,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Get users who have a specific currency in their preferences."""
    try:
        users = await user_service.get_users_by_currency(db, currency)
        return [User.model_validate(user) for user in users]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/by-impact/{impact_level}", response_model=List[User])
async def get_users_by_impact_level(
    impact_level: str,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Get users who have a specific impact level in their preferences."""
    try:
        users = await user_service.get_users_by_impact_level(db, impact_level)
        return [User.model_validate(user) for user in users]
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{telegram_id}/update-activity")
async def update_user_activity(
    telegram_id: int,
    db: AsyncSession = Depends(get_database),
    user_service: UserService = Depends(get_user_service),
):
    """Update user's last active timestamp."""
    try:
        await user_service.update_last_active(db, telegram_id)
        return {"message": "Activity updated successfully"}
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
