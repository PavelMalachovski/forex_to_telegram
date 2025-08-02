import logging
from typing import List, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, time
from sqlalchemy import text

from .database_service import ForexNewsService

logger = logging.getLogger(__name__)

# Available currencies for selection
AVAILABLE_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD",
    "CNY", "INR", "BRL", "RUB", "KRW", "MXN", "SGD", "HKD"
]

# Available impact levels
IMPACT_LEVELS = ["high", "medium", "low"]

# Available notification minutes
NOTIFICATION_MINUTES = [15, 30, 60]

# Available timezones (common ones)
AVAILABLE_TIMEZONES = [
    "Europe/Prague", "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", "Australia/Sydney",
    "UTC"
]


class UserSettingsHandler:
    """Handles user settings and preferences management."""

    def __init__(self, db_service: ForexNewsService, digest_scheduler=None):
        self.db_service = db_service
        self.digest_scheduler = digest_scheduler

    def get_settings_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate settings keyboard with current user preferences."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            markup = InlineKeyboardMarkup(row_width=2)

            # Current preferences display
            currencies = user.get_currencies_list()
            impact_levels = user.get_impact_levels_list()
            analysis_status = "✅" if user.analysis_required else "❌"
            digest_time = user.digest_time.strftime("%H:%M") if user.digest_time else "08:00"

            # Check if notification columns exist in database
            notification_available = False
            try:
                with self.db_service.db_manager.get_session() as session:
                    result = session.execute(text("""
                        SELECT column_name
                    FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name IN ('notifications_enabled', 'notification_minutes', 'notification_impact_levels')
                    """))
                    notification_columns = [row[0] for row in result]
                    # Show notification button if at least notifications_enabled column exists
                    notification_available = 'notifications_enabled' in notification_columns
                    logger.info(f"User {user_id}: Notification columns found: {notification_columns}, notification_available: {notification_available}")
            except Exception as e:
                logger.error(f"Error checking notification columns for user {user_id}: {e}")
                notification_available = False

            # Only show notification button if columns exist
            if notification_available:
                notification_status = "✅" if getattr(user, 'notifications_enabled', False) else "❌"
                markup.add(InlineKeyboardButton(
                    f"🔔 Notifications: {notification_status}",
                    callback_data="settings_notifications"
                ))
                logger.info(f"User {user_id}: Added notification button to settings")
            else:
                logger.info(f"User {user_id}: Notification button not added (columns not available)")

            # Debug: Check if user object has notification attributes
            has_notifications_enabled = hasattr(user, 'notifications_enabled')
            has_notification_minutes = hasattr(user, 'notification_minutes')
            has_notification_impact_levels = hasattr(user, 'notification_impact_levels')
            logger.info(f"User {user_id}: has_notifications_enabled={has_notifications_enabled}, has_notification_minutes={has_notification_minutes}, has_notification_impact_levels={has_notification_impact_levels}")

            markup.add(InlineKeyboardButton(
                f"💰 Currencies: {', '.join(currencies) if currencies else 'All'}",
                callback_data="settings_currencies"
            ))
            markup.add(InlineKeyboardButton(
                f"📊 Impact: {', '.join(impact_levels)}",
                callback_data="settings_impact"
            ))
            markup.add(InlineKeyboardButton(
                f"🤖 Analysis: {analysis_status}",
                callback_data="settings_analysis"
            ))
            markup.add(InlineKeyboardButton(
                f"⏰ Digest Time: {digest_time}",
                callback_data="settings_digest_time"
            ))
            markup.add(InlineKeyboardButton(
                f"🌍 Timezone: {user.get_timezone()}",
                callback_data="settings_timezone"
            ))

            return markup
        except Exception as e:
            logger.error(f"Error generating settings keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_currencies_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate currencies selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            selected_currencies = set(user.get_currencies_list())

            markup = InlineKeyboardMarkup(row_width=4)

            # Add currency buttons
            for currency in AVAILABLE_CURRENCIES:
                status = "✅" if currency in selected_currencies else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {currency}",
                    callback_data=f"currency_{currency}"
                ))

            # Add control buttons
            markup.add(
                InlineKeyboardButton("✅ Select All", callback_data="currency_select_all"),
                InlineKeyboardButton("❌ Clear All", callback_data="currency_clear_all")
            )
            markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))

            return markup
        except Exception as e:
            logger.error(f"Error generating currencies keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_impact_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate impact levels selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            selected_impacts = set(user.get_impact_levels_list())

            markup = InlineKeyboardMarkup(row_width=2)

            for impact in IMPACT_LEVELS:
                status = "✅" if impact in selected_impacts else "⬜"
                emoji = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(impact, "⚪")
                markup.add(InlineKeyboardButton(
                    f"{status} {emoji} {impact.capitalize()}",
                    callback_data=f"impact_{impact}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))

            return markup
        except Exception as e:
            logger.error(f"Error generating impact keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_digest_time_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate custom time picker keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_time = user.digest_time if user.digest_time else time(8, 0)
            current_hour = current_time.hour
            current_minute = current_time.minute

            markup = InlineKeyboardMarkup(row_width=3)

            # Hour selection (0-23)
            markup.add(InlineKeyboardButton("🕐 Hour", callback_data="time_hour"))
            markup.add(InlineKeyboardButton(f"⏰ {current_hour:02d}:{current_minute:02d}", callback_data="time_current"))
            markup.add(InlineKeyboardButton("🕐 Minute", callback_data="time_minute"))

            markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))

            return markup
        except Exception as e:
            logger.error(f"Error generating digest time keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_hour_picker_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate hour picker keyboard (0-23)."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_time = user.digest_time if user.digest_time else time(8, 0)
            current_hour = current_time.hour

            markup = InlineKeyboardMarkup(row_width=6)

            # Hour buttons (0-23)
            for hour in range(24):
                status = "✅" if hour == current_hour else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {hour:02d}",
                    callback_data=f"hour_{hour:02d}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Time", callback_data="settings_digest_time"))

            return markup
        except Exception as e:
            logger.error(f"Error generating hour picker keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_minute_picker_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate minute picker keyboard (0-59, in 5-minute intervals)."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_time = user.digest_time if user.digest_time else time(8, 0)
            current_minute = current_time.minute

            markup = InlineKeyboardMarkup(row_width=6)

            # Minute buttons (0-59, in 5-minute intervals)
            for minute in range(0, 60, 5):
                status = "✅" if minute == current_minute else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {minute:02d}",
                    callback_data=f"minute_{minute:02d}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Time", callback_data="settings_digest_time"))

            return markup
        except Exception as e:
            logger.error(f"Error generating minute picker keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_timezone_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate timezone selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_timezone = user.get_timezone()

            markup = InlineKeyboardMarkup(row_width=2)

            # Add timezone buttons
            for timezone in AVAILABLE_TIMEZONES:
                status = "✅" if timezone == current_timezone else "⬜"
                # Create a shorter display name for the timezone
                display_name = timezone.replace("Europe/", "").replace("America/", "").replace("Asia/", "").replace("Australia/", "")
                markup.add(InlineKeyboardButton(
                    f"{status} {display_name}",
                    callback_data=f"timezone_{timezone}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))

            return markup
        except Exception as e:
            logger.error(f"Error generating timezone keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_notifications_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate notifications settings keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)

            # Check if notification fields exist
            if not hasattr(user, 'notifications_enabled'):
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton(
                    "⚠️ Notifications not available yet",
                    callback_data="IGNORE"
                ))
                markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))
                return markup

            notification_status = "✅" if user.notifications_enabled else "❌"
            notification_minutes = getattr(user, 'notification_minutes', 30)
            notification_impacts = user.get_notification_impact_levels_list()

            markup = InlineKeyboardMarkup(row_width=2)

            # Enable/Disable notifications
            markup.add(InlineKeyboardButton(
                f"🔔 Notifications: {notification_status}",
                callback_data="notification_toggle"
            ))

            # Notification timing
            markup.add(InlineKeyboardButton(
                f"⏱️ Alert {notification_minutes} min before",
                callback_data="notification_timing"
            ))

            # Notification impact levels
            markup.add(InlineKeyboardButton(
                f"📊 Alert for: {', '.join(notification_impacts)}",
                callback_data="notification_impact"
            ))

            # Chart settings
            charts_enabled = getattr(user, 'charts_enabled', False)
            chart_status = "✅" if charts_enabled else "❌"
            chart_type = getattr(user, 'chart_type', 'single')

            markup.add(InlineKeyboardButton(
                f"📈 Charts: {chart_status} ({chart_type})",
                callback_data="settings_charts"
            ))

            markup.add(InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back"))

            return markup
        except Exception as e:
            logger.error(f"Error generating notifications keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_notification_timing_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate notification timing selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)

            # Check if notification fields exist
            if not hasattr(user, 'notification_minutes'):
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton(
                    "⚠️ Notifications not available yet",
                    callback_data="IGNORE"
                ))
                markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))
                return markup

            current_minutes = getattr(user, 'notification_minutes', 30)

            markup = InlineKeyboardMarkup(row_width=3)

            for minutes in NOTIFICATION_MINUTES:
                status = "✅" if minutes == current_minutes else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {minutes} min",
                    callback_data=f"notification_minutes_{minutes}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))

            return markup
        except Exception as e:
            logger.error(f"Error generating notification timing keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_notification_impact_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate notification impact levels selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)

            # Check if notification fields exist
            if not hasattr(user, 'notification_impact_levels'):
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton(
                    "⚠️ Notifications not available yet",
                    callback_data="IGNORE"
                ))
                markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))
                return markup

            selected_impacts = set(user.get_notification_impact_levels_list())

            markup = InlineKeyboardMarkup(row_width=2)

            for impact in IMPACT_LEVELS:
                status = "✅" if impact in selected_impacts else "⬜"
                emoji = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(impact, "⚪")
                markup.add(InlineKeyboardButton(
                    f"{status} {emoji} {impact.capitalize()}",
                    callback_data=f"notification_impact_{impact}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))

            return markup
        except Exception as e:
            logger.error(f"Error generating notification impact keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_charts_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate chart settings keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)

            # Check if chart fields exist
            if not hasattr(user, 'charts_enabled'):
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton(
                    "⚠️ Chart settings not available yet",
                    callback_data="IGNORE"
                ))
                markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))
                return markup

            charts_enabled = getattr(user, 'charts_enabled', False)
            chart_type = getattr(user, 'chart_type', 'single')
            window_hours = getattr(user, 'chart_window_hours', 2)

            markup = InlineKeyboardMarkup(row_width=2)

            # Enable/Disable charts
            markup.add(InlineKeyboardButton(
                f"📈 Charts: {'✅' if charts_enabled else '❌'}",
                callback_data="chart_toggle"
            ))

            # Chart type selection
            markup.add(InlineKeyboardButton(
                f"📊 Type: {chart_type.title()}",
                callback_data="chart_type"
            ))

            # Chart window hours
            markup.add(InlineKeyboardButton(
                f"⏱️ Window: {window_hours}h",
                callback_data="chart_window"
            ))

            markup.add(InlineKeyboardButton("🔙 Back to Notifications", callback_data="settings_notifications"))

            return markup
        except Exception as e:
            logger.error(f"Error generating charts keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_chart_type_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate chart type selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_type = getattr(user, 'chart_type', 'single')

            markup = InlineKeyboardMarkup(row_width=2)

            chart_types = [
                ('single', 'Single Pair'),
                ('multi', 'Multi Pair'),
                ('none', 'No Charts')
            ]

            for chart_type, display_name in chart_types:
                status = "✅" if chart_type == current_type else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {display_name}",
                    callback_data=f"chart_type_{chart_type}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Charts", callback_data="settings_charts"))

            return markup
        except Exception as e:
            logger.error(f"Error generating chart type keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def get_chart_window_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate chart window hours selection keyboard."""
        try:
            user = self.db_service.get_or_create_user(user_id)
            current_hours = getattr(user, 'chart_window_hours', 2)

            markup = InlineKeyboardMarkup(row_width=3)

            window_options = [1, 2, 4, 6]

            for hours in window_options:
                status = "✅" if hours == current_hours else "⬜"
                markup.add(InlineKeyboardButton(
                    f"{status} {hours}h",
                    callback_data=f"chart_window_{hours}"
                ))

            markup.add(InlineKeyboardButton("🔙 Back to Charts", callback_data="settings_charts"))

            return markup
        except Exception as e:
            logger.error(f"Error generating chart window keyboard for user {user_id}: {e}")
            return InlineKeyboardMarkup()

    def _refresh_digest_jobs(self):
        """Refresh digest jobs when user preferences change."""
        try:
            if self.digest_scheduler:
                self.digest_scheduler.refresh_digest_jobs()
                logger.info("Refreshed digest jobs after user preference change")
        except Exception as e:
            logger.error(f"Error refreshing digest jobs: {e}")

    def handle_settings_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle settings callback and return (handled, message, markup)."""
        try:
            data = call.data
            user_id = call.from_user.id

            if data == "settings_currencies":
                markup = self.get_currencies_keyboard(user_id)
                return True, "Select your preferred currencies:", markup

            elif data == "settings_impact":
                markup = self.get_impact_keyboard(user_id)
                return True, "Select impact levels you want to receive:", markup

            elif data == "settings_analysis":
                user = self.db_service.get_or_create_user(user_id)
                new_analysis = not user.analysis_required
                self.db_service.update_user_preferences(user_id, analysis_required=new_analysis)
                status = "enabled" if new_analysis else "disabled"
                markup = self.get_settings_keyboard(user_id)
                return True, f"✅ AI analysis {status}!", markup

            elif data == "settings_digest_time":
                markup = self.get_digest_time_keyboard(user_id)
                return True, "Select your preferred daily digest time:", markup

            elif data == "settings_back":
                markup = self.get_settings_keyboard(user_id)
                return True, "⚙️ Your Settings:", markup

            elif data == "settings_notifications":
                markup = self.get_notifications_keyboard(user_id)
                return True, "Configure your notifications:", markup

            elif data == "settings_timezone":
                markup = self.get_timezone_keyboard(user_id)
                return True, "Select your timezone:", markup

            elif data == "notification_toggle":
                user = self.db_service.get_or_create_user(user_id)
                if not hasattr(user, 'notifications_enabled'):
                    markup = self.get_notifications_keyboard(user_id)
                    return True, "⚠️ Notifications not available yet. Please run database migration first.", markup

                new_notifications_enabled = not user.notifications_enabled
                self.db_service.update_user_preferences(user_id, notifications_enabled=new_notifications_enabled)
                status = "enabled" if new_notifications_enabled else "disabled"
                markup = self.get_notifications_keyboard(user_id)
                return True, f"✅ Notifications {status}!", markup

            elif data == "notification_timing":
                markup = self.get_notification_timing_keyboard(user_id)
                return True, "Select notification timing:", markup

            elif data == "notification_impact":
                markup = self.get_notification_impact_keyboard(user_id)
                return True, "Select notification impact levels:", markup

            elif data.startswith("currency_"):
                return self._handle_currency_callback(call)

            elif data.startswith("impact_"):
                return self._handle_impact_callback(call)

            elif data.startswith("time_"):
                return self._handle_time_callback(call)

            elif data.startswith("hour_"):
                return self._handle_hour_callback(call)

            elif data.startswith("minute_"):
                return self._handle_minute_callback(call)

            elif data.startswith("timezone_"):
                return self._handle_timezone_callback(call)

            elif data.startswith("notification_minutes_"):
                minutes_str = data.replace("notification_minutes_", "")
                try:
                    minutes = int(minutes_str)
                    if minutes in NOTIFICATION_MINUTES:
                        user = self.db_service.get_or_create_user(user_id)
                        if not hasattr(user, 'notification_minutes'):
                            markup = self.get_notification_timing_keyboard(user_id)
                            return True, "⚠️ Notifications not available yet. Please run database migration first.", markup

                        self.db_service.update_user_preferences(user_id, notification_minutes=minutes)
                        markup = self.get_notification_timing_keyboard(user_id)
                        return True, f"✅ Notification timing set to {minutes} minutes!", markup
                except Exception as e:
                    logger.error(f"Error setting notification minutes: {e}")
                    return False, "", None

            elif data.startswith("notification_impact_"):
                impact = data.replace("notification_impact_", "")
                if impact in IMPACT_LEVELS:
                    user = self.db_service.get_or_create_user(user_id)
                    if not hasattr(user, 'notification_impact_levels'):
                        markup = self.get_notification_impact_keyboard(user_id)
                        return True, "⚠️ Notifications not available yet. Please run database migration first.", markup

            elif data == "settings_charts":
                markup = self.get_charts_keyboard(user_id)
                return True, "Configure your chart settings:", markup

            elif data == "chart_toggle":
                user = self.db_service.get_or_create_user(user_id)
                if not hasattr(user, 'charts_enabled'):
                    markup = self.get_charts_keyboard(user_id)
                    return True, "⚠️ Chart settings not available yet. Please run database migration first.", markup

                new_charts_enabled = not user.charts_enabled
                self.db_service.update_user_preferences(user_id, charts_enabled=new_charts_enabled)
                status = "enabled" if new_charts_enabled else "disabled"
                markup = self.get_charts_keyboard(user_id)
                return True, f"✅ Charts {status}!", markup

            elif data == "chart_type":
                markup = self.get_chart_type_keyboard(user_id)
                return True, "Select chart type:", markup

            elif data == "chart_window":
                markup = self.get_chart_window_keyboard(user_id)
                return True, "Select chart window hours:", markup

            elif data.startswith("chart_type_"):
                chart_type = data.replace("chart_type_", "")
                if chart_type in ['single', 'multi', 'none']:
                    user = self.db_service.get_or_create_user(user_id)
                    if not hasattr(user, 'chart_type'):
                        markup = self.get_chart_type_keyboard(user_id)
                        return True, "⚠️ Chart settings not available yet. Please run database migration first.", markup

                    self.db_service.update_user_preferences(user_id, chart_type=chart_type)
                    markup = self.get_chart_type_keyboard(user_id)
                    return True, f"✅ Chart type set to {chart_type.title()}!", markup

            elif data.startswith("chart_window_"):
                hours_str = data.replace("chart_window_", "")
                try:
                    hours = int(hours_str)
                    if hours in [1, 2, 4, 6]:
                        user = self.db_service.get_or_create_user(user_id)
                        if not hasattr(user, 'chart_window_hours'):
                            markup = self.get_chart_window_keyboard(user_id)
                            return True, "⚠️ Chart settings not available yet. Please run database migration first.", markup

                        self.db_service.update_user_preferences(user_id, chart_window_hours=hours)
                        markup = self.get_chart_window_keyboard(user_id)
                        return True, f"✅ Chart window set to {hours} hours!", markup
                except Exception as e:
                    logger.error(f"Error setting chart window hours: {e}")
                    return False, "", None

                    current_impacts = set(user.get_notification_impact_levels_list())
                    if impact in current_impacts:
                        current_impacts.remove(impact)
                    else:
                        current_impacts.add(impact)

                    # Ensure at least one impact level is selected
                    if not current_impacts:
                        current_impacts.add("high")

                    new_impacts_list = list(current_impacts)
                    self.db_service.update_user_preferences(user_id, notification_impact_levels=",".join(new_impacts_list))
                    markup = self.get_notification_impact_keyboard(user_id)
                    return True, f"✅ Notification impact level {impact} {'added' if impact in current_impacts else 'removed'}!", markup

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling settings callback: {e}")
            return False, "", None

    def _handle_currency_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle currency selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id
            user = self.db_service.get_or_create_user(user_id)
            current_currencies = set(user.get_currencies_list())

            if data == "currency_select_all":
                new_currencies = AVAILABLE_CURRENCIES.copy()
                self.db_service.update_user_preferences(user_id, preferred_currencies=",".join(new_currencies))
                markup = self.get_currencies_keyboard(user_id)
                return True, "✅ All currencies selected!", markup

            elif data == "currency_clear_all":
                self.db_service.update_user_preferences(user_id, preferred_currencies="")
                markup = self.get_currencies_keyboard(user_id)
                return True, "❌ All currencies cleared!", markup

            elif data.startswith("currency_"):
                currency = data.replace("currency_", "")
                if currency in AVAILABLE_CURRENCIES:
                    if currency in current_currencies:
                        current_currencies.remove(currency)
                    else:
                        current_currencies.add(currency)

                    new_currencies_list = list(current_currencies)
                    self.db_service.update_user_preferences(user_id, preferred_currencies=",".join(new_currencies_list))
                    markup = self.get_currencies_keyboard(user_id)
                    return True, f"✅ Currency {currency} {'added' if currency in current_currencies else 'removed'}!", markup

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling currency callback: {e}")
            return False, "", None

    def _handle_impact_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle impact level selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id
            user = self.db_service.get_or_create_user(user_id)
            current_impacts = set(user.get_impact_levels_list())

            if data.startswith("impact_"):
                impact = data.replace("impact_", "")
                if impact in IMPACT_LEVELS:
                    if impact in current_impacts:
                        current_impacts.remove(impact)
                    else:
                        current_impacts.add(impact)

                    # Ensure at least one impact level is selected
                    if not current_impacts:
                        current_impacts.add("high")

                    new_impacts_list = list(current_impacts)
                    self.db_service.update_user_preferences(user_id, impact_levels=",".join(new_impacts_list))
                    markup = self.get_impact_keyboard(user_id)
                    return True, f"✅ Impact level {impact} {'added' if impact in current_impacts else 'removed'}!", markup

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling impact callback: {e}")
            return False, "", None

    def _handle_time_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle time selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id

            if data == "time_hour":
                markup = self.get_hour_picker_keyboard(user_id)
                return True, "Select hour (0-23):", markup

            elif data == "time_minute":
                markup = self.get_minute_picker_keyboard(user_id)
                return True, "Select minute (0-59, 5-minute intervals):", markup

            elif data == "time_current":
                user = self.db_service.get_or_create_user(user_id)
                current_time = user.digest_time if user.digest_time else time(8, 0)
                markup = self.get_settings_keyboard(user_id)
                return True, f"⏰ Current digest time: {current_time.strftime('%H:%M')}", markup

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling time callback: {e}")
            return False, "", None

    def _handle_hour_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle hour selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id

            if data.startswith("hour_"):
                hour_str = data.replace("hour_", "")
                try:
                    hour = int(hour_str)
                    if 0 <= hour <= 23:
                        user = self.db_service.get_or_create_user(user_id)
                        current_time = user.digest_time if user.digest_time else time(8, 0)
                        new_time = time(hour, current_time.minute)
                        self.db_service.update_user_preferences(user_id, digest_time=new_time)
                        self._refresh_digest_jobs()
                        markup = self.get_digest_time_keyboard(user_id)
                        return True, f"✅ Hour set to {hour:02d}!", markup
                except Exception as e:
                    logger.error(f"Error setting hour: {e}")
                    return False, "", None

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling hour callback: {e}")
            return False, "", None

    def _handle_minute_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle minute selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id

            if data.startswith("minute_"):
                minute_str = data.replace("minute_", "")
                try:
                    minute = int(minute_str)
                    if 0 <= minute <= 59:
                        user = self.db_service.get_or_create_user(user_id)
                        current_time = user.digest_time if user.digest_time else time(8, 0)
                        new_time = time(current_time.hour, minute)
                        self.db_service.update_user_preferences(user_id, digest_time=new_time)
                        self._refresh_digest_jobs()
                        markup = self.get_digest_time_keyboard(user_id)
                        return True, f"✅ Minute set to {minute:02d}!", markup
                except Exception as e:
                    logger.error(f"Error setting minute: {e}")
                    return False, "", None

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling minute callback: {e}")
            return False, "", None

    def _handle_timezone_callback(self, call: CallbackQuery) -> tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """Handle timezone selection callbacks."""
        try:
            data = call.data
            user_id = call.from_user.id

            if data.startswith("timezone_"):
                timezone = data.replace("timezone_", "")
                if timezone in AVAILABLE_TIMEZONES:
                    user = self.db_service.get_or_create_user(user_id)
                    if not hasattr(user, 'timezone'):
                        markup = self.get_timezone_keyboard(user_id)
                        return True, "⚠️ Timezone not available yet. Please run database migration first.", markup

                    self.db_service.update_user_preferences(user_id, timezone=timezone)
                    markup = self.get_timezone_keyboard(user_id)
                    display_name = timezone.replace("Europe/", "").replace("America/", "").replace("Asia/", "").replace("Australia/", "")
                    return True, f"✅ Timezone set to {display_name}!", markup

            return False, "", None

        except Exception as e:
            logger.error(f"Error handling timezone callback: {e}")
            return False, "", None
