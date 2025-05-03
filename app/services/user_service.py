
"""
User service for managing bot users and their preferences.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.database.models import BotUser, Currency, UserCurrencyPreference
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing bot users."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_user(
        self,
        telegram_user_id: int,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> BotUser:
        """
        Get existing user or create a new one.
        
        Args:
            telegram_user_id: Telegram user ID
            telegram_username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: User's language code
            
        Returns:
            BotUser object
        """
        user = self.db.query(BotUser).filter(
            BotUser.telegram_user_id == telegram_user_id
        ).first()
        
        if user:
            # Update user information
            user.telegram_username = telegram_username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.is_active = True
            logger.info(f"Updated user: {telegram_user_id}")
        else:
            # Create new user
            user = BotUser(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code
            )
            self.db.add(user)
            logger.info(f"Created new user: {telegram_user_id}")
        
        self.db.commit()
        return user
    
    def get_user_currency_preferences(self, telegram_user_id: int) -> List[str]:
        """
        Get user's currency preferences.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            List of currency codes
        """
        user = self.db.query(BotUser).filter(
            BotUser.telegram_user_id == telegram_user_id
        ).first()
        
        if not user:
            return []
        
        preferences = self.db.query(UserCurrencyPreference).options(
            joinedload(UserCurrencyPreference.currency)
        ).filter(
            UserCurrencyPreference.user_id == user.id
        ).all()
        
        return [pref.currency.code for pref in preferences]
    
    def set_user_currency_preferences(
        self, 
        telegram_user_id: int, 
        currency_codes: List[str]
    ) -> None:
        """
        Set user's currency preferences.
        
        Args:
            telegram_user_id: Telegram user ID
            currency_codes: List of currency codes to set as preferences
        """
        user = self.get_or_create_user(telegram_user_id)
        
        # Remove existing preferences
        self.db.query(UserCurrencyPreference).filter(
            UserCurrencyPreference.user_id == user.id
        ).delete()
        
        # Add new preferences
        for currency_code in currency_codes:
            currency = self.db.query(Currency).filter(
                Currency.code == currency_code
            ).first()
            
            if currency:
                preference = UserCurrencyPreference(
                    user_id=user.id,
                    currency_id=currency.id
                )
                self.db.add(preference)
        
        self.db.commit()
        logger.info(f"Set currency preferences for user {telegram_user_id}: {currency_codes}")
    
    def add_user_currency_preference(
        self, 
        telegram_user_id: int, 
        currency_code: str
    ) -> bool:
        """
        Add a currency preference for a user.
        
        Args:
            telegram_user_id: Telegram user ID
            currency_code: Currency code to add
            
        Returns:
            True if added successfully, False if already exists
        """
        user = self.get_or_create_user(telegram_user_id)
        
        currency = self.db.query(Currency).filter(
            Currency.code == currency_code
        ).first()
        
        if not currency:
            logger.warning(f"Currency {currency_code} not found")
            return False
        
        # Check if preference already exists
        existing = self.db.query(UserCurrencyPreference).filter(
            and_(
                UserCurrencyPreference.user_id == user.id,
                UserCurrencyPreference.currency_id == currency.id
            )
        ).first()
        
        if existing:
            return False
        
        # Add new preference
        preference = UserCurrencyPreference(
            user_id=user.id,
            currency_id=currency.id
        )
        self.db.add(preference)
        self.db.commit()
        
        logger.info(f"Added currency preference {currency_code} for user {telegram_user_id}")
        return True
    
    def remove_user_currency_preference(
        self, 
        telegram_user_id: int, 
        currency_code: str
    ) -> bool:
        """
        Remove a currency preference for a user.
        
        Args:
            telegram_user_id: Telegram user ID
            currency_code: Currency code to remove
            
        Returns:
            True if removed successfully, False if not found
        """
        user = self.db.query(BotUser).filter(
            BotUser.telegram_user_id == telegram_user_id
        ).first()
        
        if not user:
            return False
        
        currency = self.db.query(Currency).filter(
            Currency.code == currency_code
        ).first()
        
        if not currency:
            return False
        
        # Remove preference
        deleted = self.db.query(UserCurrencyPreference).filter(
            and_(
                UserCurrencyPreference.user_id == user.id,
                UserCurrencyPreference.currency_id == currency.id
            )
        ).delete()
        
        self.db.commit()
        
        if deleted:
            logger.info(f"Removed currency preference {currency_code} for user {telegram_user_id}")
            return True
        
        return False
    
    def get_active_users_with_notifications(self) -> List[BotUser]:
        """
        Get all active users who have notifications enabled.
        
        Returns:
            List of active BotUser objects with notifications enabled
        """
        users = self.db.query(BotUser).filter(
            and_(
                BotUser.is_active == True,
                BotUser.notifications_enabled == True
            )
        ).all()
        
        logger.info(f"Found {len(users)} active users with notifications enabled")
        return users
    
    def create_or_get_user(
        self,
        telegram_user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> BotUser:
        """
        Create or get user (alias for get_or_create_user for compatibility).
        
        Args:
            telegram_user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            BotUser object
        """
        return self.get_or_create_user(
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=last_name
        )
    
    def get_all_users_with_currency_preference(self, currency_code: str) -> List[BotUser]:
        """
        Get all users who have a specific currency preference.
        
        Args:
            currency_code: Currency code to filter by
            
        Returns:
            List of BotUser objects
        """
        users = self.db.query(BotUser).join(
            UserCurrencyPreference
        ).join(
            Currency
        ).filter(
            and_(
                Currency.code == currency_code,
                BotUser.is_active == True
            )
        ).all()
        
        return users
    
    def get_user_by_telegram_id(self, telegram_user_id: int) -> Optional[BotUser]:
        """
        Get user by Telegram user ID.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            BotUser object or None if not found
        """
        user = self.db.query(BotUser).filter(
            BotUser.telegram_user_id == telegram_user_id
        ).first()
        
        return user
    
    def create_or_get_user(
        self,
        telegram_user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> BotUser:
        """
        Create or get user (alias for get_or_create_user for backward compatibility).
        
        Args:
            telegram_user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: User's language code
            
        Returns:
            BotUser object
        """
        return self.get_or_create_user(
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
    
    def update_user_preferences(
        self,
        telegram_user_id: int,
        currency_preference: Optional[str] = None,
        notifications_enabled: Optional[bool] = None
    ) -> Optional[BotUser]:
        """
        Update user preferences.
        
        Args:
            telegram_user_id: Telegram user ID
            currency_preference: Currency preference code
            notifications_enabled: Whether notifications are enabled
            
        Returns:
            Updated BotUser object or None if user not found
        """
        user = self.get_user_by_telegram_id(telegram_user_id)
        
        if not user:
            return None
        
        if currency_preference is not None:
            user.currency_preference = currency_preference
        
        if notifications_enabled is not None:
            user.notifications_enabled = notifications_enabled
        
        self.db.commit()
        logger.info(f"Updated preferences for user {telegram_user_id}")
        
        return user
