import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import text
from io import BytesIO

from .database_service import ForexNewsService
from .chart_service import chart_service
from .config import Config

logger = logging.getLogger(__name__)


class VisualizeHandler:
    """Handler for the /visualize command and related functionality."""

    def __init__(self, db_service: ForexNewsService, config: Config):
        self.db_service = db_service
        self.config = config
        # Pruned currency list per request
        # Include major FX plus commodities/crypto requested
        self.available_currencies = [
            "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD",
            "XAU", "BTC", "ETH"
        ]
        # Limit to only 1h and 2h symmetric windows
        self.time_windows = [
            ("1h", 1),
            ("2h", 2)
        ]

        # Asymmetric time windows for cross-rate analysis
        # Limit to only 1h before → 1h after and 2h before → 2h after
        self.cross_rate_windows = [
            ("1h before → 1h after", 1, 1),
            ("2h before → 2h after", 2, 2),
        ]

    def handle_visualize_command(self, message, bot):
        """Handle the /visualize command - show currency selection."""
        keyboard = []
        row = []

        for currency in self.available_currencies:
            row.append(InlineKeyboardButton(currency, callback_data=f"viz_currency_{currency}"))
            if len(row) == 3:  # 3 buttons per row
                keyboard.append(row)
                row = []

        if row:  # Add remaining buttons
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.send_message(
            message.chat.id,
            "📊 **Chart Visualization**\n\n"
            "Select a currency to view available events and generate charts:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def handle_currency_selection(self, call: CallbackQuery, bot):
        """Handle currency selection - show unique events for the selected currency."""
        currency = call.data.replace("viz_currency_", "")

        # Get unique events for this currency from the database
        unique_events = self._get_unique_events_for_currency(currency)

        if not unique_events:
            bot.edit_message_text(
                f"❌ No events found for {currency}.\n\n"
                "Try selecting a different currency or check if there are events in the database.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)
            return
        # Show first page
        self._render_events_page(bot, call, currency, unique_events, page=0)
        bot.answer_callback_query(call.id)

    def handle_event_name_selection(self, call: CallbackQuery, bot):
        """Handle event name selection - show dates for this specific event."""
        # Parse callback data: viz_event_name_CURRENCY_EVENTNAME[__pgN]
        payload = call.data.replace("viz_event_name_", "")
        callback_parts = payload.split("_", 1)
        currency = callback_parts[0]
        raw_event = callback_parts[1] if len(callback_parts) > 1 else ""
        page = 0
        if raw_event.endswith("__pg0") or "__pg" in raw_event:
            try:
                raw_event, pg = raw_event.rsplit("__pg", 1)
                page = int(pg)
            except Exception:
                page = 0
        event_name = raw_event

        # Get dates for this specific event
        event_dates = self._get_dates_for_event(currency, event_name)

        if not event_dates:
            bot.edit_message_text(
                f"❌ No dates found for this event.\n\n"
                f"**Event:** {event_name}\n"
                f"**Currency:** {currency}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)
            return

        # Create keyboard with event dates (paginated)
        PAGE_SIZE = 12
        total = len(event_dates)
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = event_dates[start:end]

        keyboard = []
        for event_data in page_items:
            date_time_str = f"{event_data['date']} {event_data['time']}"
            impact_emoji = {
                'high': '🔴',
                'medium': '🟠',
                'low': '🟡'
            }.get(event_data.get('impact_level', 'medium'), '🟠')

            button_text = f"{impact_emoji} {date_time_str}"
            callback_data = f"viz_event_{currency}_{event_data['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Add pagination row if needed
        max_page = (total - 1) // PAGE_SIZE if total else 0
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"viz_event_name_{currency}_{event_name}__pg{page-1}"))
        if page < max_page:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"viz_event_name_{currency}_{event_name}__pg{page+1}"))
        if nav_row:
            keyboard.append(nav_row)

        # Add back buttons
        keyboard.append([InlineKeyboardButton("🔙 Back to Events", callback_data=f"viz_currency_{currency}")])
        keyboard.append([InlineKeyboardButton("🏠 Back to Currencies", callback_data="viz_back_currencies")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Clean event name for display
        clean_event_name = str(event_name).replace('\\', '')

        bot.edit_message_text(
            f"📅 **Dates for Event**\n\n"
            f"**Event:** {clean_event_name}\n"
            f"**Currency:** {currency}\n\n"
            f"Found {len(event_dates)} occurrences. Select a date to generate chart:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    def _render_events_page(self, bot, call: CallbackQuery, currency: str, unique_events: List[str], page: int):
        PAGE_SIZE = 10
        total = len(unique_events)
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_events = unique_events[start:end]

        keyboard = []
        for event_name in page_events:
            display_name = event_name[:40] + "..." if len(event_name) > 40 else event_name
            callback_data = f"viz_event_name_{currency}_{event_name[:50]}"
            keyboard.append([InlineKeyboardButton(f"📊 {display_name}", callback_data=callback_data)])

        # Pagination controls
        max_page = (total - 1) // PAGE_SIZE if total else 0
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"viz_events_{currency}_{page-1}"))
        if page < max_page:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"viz_events_{currency}_{page+1}"))
        if nav_row:
            keyboard.append(nav_row)

        # Back
        keyboard.append([InlineKeyboardButton("🔙 Back to Currencies", callback_data="viz_back_currencies")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            f"📈 **Events for {currency}**\n\n"
            f"Found {total} unique events. Select an event to see available dates (page {page+1}/{max_page+1}):",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def handle_events_page(self, call: CallbackQuery, bot):
        # Parse callback data: viz_events_CURRENCY_PAGE
        payload = call.data.replace("viz_events_", "")
        try:
            currency, page_str = payload.rsplit("_", 1)
            page = int(page_str)
        except Exception:
            currency, page = payload, 0
        unique_events = self._get_unique_events_for_currency(currency)
        self._render_events_page(bot, call, currency, unique_events, page)
        bot.answer_callback_query(call.id)

    def handle_event_selection(self, call: CallbackQuery, bot):
        """Handle specific event date selection - show time window options."""
        # Parse callback data: viz_event_CURRENCY_EVENTID
        parts = call.data.split("_")
        currency = parts[2]
        event_id = parts[3]

        # Get event details
        event = self._get_event_by_id(event_id)
        if not event:
            bot.edit_message_text(
                "❌ Event not found.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            bot.answer_callback_query(call.id)
            return

        # Check if this is a future event
        event_date = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        is_future = event_date > now

        if is_future:
            # For future events, show a warning message
            # Clean event name for display
            clean_event_name = str(event['event']).replace('\\', '')

            bot.edit_message_text(
                f"⏰ **Future Event**\n\n"
                f"**Event:** {clean_event_name}\n"
                f"**Date:** {event['date']} {event['time']}\n"
                f"**Currency:** {currency}\n\n"
                f"⚠️ This event is in the future. Charts can only be generated for past events.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)
            return

        # Create keyboard with chart options
        keyboard = []

        # Single currency chart options
        for window_name, window_hours in self.time_windows:
            callback_data = f"viz_chart_{currency}_{event_id}_{window_hours}"
            keyboard.append([InlineKeyboardButton(f"📊 {window_name} window ({currency} only)", callback_data=callback_data)])

        # Multi-currency chart options with asymmetric time windows
        for window_name, before_hours, after_hours in self.cross_rate_windows:
            callback_data = f"viz_multi_{currency}_{event_id}_{before_hours}_{after_hours}"
            keyboard.append([InlineKeyboardButton(f"📈 {window_name} (Cross-rate)", callback_data=callback_data)])

        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Events", callback_data=f"viz_currency_{currency}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            f"📊 **Generate Chart**\n\n"
            f"**Event:** {event['event']}\n"
            f"**Date:** {event['date']} {event['time']}\n"
            f"**Currency:** {currency}\n\n"
            "Select chart type and time window:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    def handle_chart_generation(self, call: CallbackQuery, bot):
        """Handle chart generation request."""
        # Answer callback query immediately to prevent timeout
        bot.answer_callback_query(call.id, "🔄 Generating chart...")

        # Parse callback data: viz_chart_CURRENCY_EVENTID_WINDOWHOURS
        parts = call.data.split("_")
        currency = parts[2]
        event_id = parts[3]
        window_hours = float(parts[4])

        # Get event details
        event = self._get_event_by_id(event_id)
        if not event:
            bot.edit_message_text(
                "❌ Event not found.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return

        # Clean event name for display
        clean_event_name = str(event['event']).replace('\\', '')

        # Show processing message
        bot.edit_message_text(
            f"🔄 Generating chart for {currency}...\n\n"
            f"Event: {clean_event_name}\n"
            f"Time window: ±{window_hours}h",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )

        try:
            # Generate the chart
            chart_buffer = self._generate_event_chart(event, currency, window_hours)

            if chart_buffer:
                # Send the chart
                logger.info(f"Sending single currency chart for {currency} to user {call.from_user.id}")
                try:
                    bot.send_photo(
                        chat_id=call.from_user.id,
                        photo=chart_buffer,
                        caption=f"📊 **Chart for {currency}**\n\n"
                               f"**Event:** {clean_event_name}\n"
                               f"**Date:** {event['date']} {event['time']}\n"
                               f"**Time window:** ±{window_hours}h\n"
                               f"**Impact:** {event['impact_level']}",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Successfully sent single currency chart for {currency}")
                except Exception as send_error:
                    logger.error(f"Failed to send single currency chart: {send_error}")
                    # Try sending without markdown parsing
                    try:
                        bot.send_photo(
                            chat_id=call.from_user.id,
                            photo=chart_buffer,
                            caption=f"Chart for {currency}\n\nEvent: {clean_event_name}\nDate: {event['date']} {event['time']}\nTime window: ±{window_hours}h\nImpact: {event['impact_level']}"
                        )
                        logger.info(f"Successfully sent single currency chart without markdown for {currency}")
                    except Exception as fallback_error:
                        logger.error(f"Failed to send single currency chart even without markdown: {fallback_error}")
                        raise send_error  # Re-raise original error

                # Show success message with options
                keyboard = [
                    [InlineKeyboardButton("📊 Generate Another Chart", callback_data=f"viz_event_{currency}_{event_id}")],
                    [InlineKeyboardButton("🔙 Back to Events", callback_data=f"viz_currency_{currency}")],
                    [InlineKeyboardButton("🏠 Back to Currencies", callback_data="viz_back_currencies")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                bot.edit_message_text(
                    f"✅ **Chart Generated Successfully!**\n\n"
                    f"Chart for {currency} event has been sent.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                # Check if it's a future event
                event_date = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
                now = datetime.now()

                if event_date > now:
                    error_message = f"❌ **Chart Generation Failed**\n\n" \
                                  f"Cannot generate chart for future events.\n" \
                                  f"Event date: {event['date']} {event['time']}\n" \
                                  f"Current time: {now.strftime('%Y-%m-%d %H:%M')}"
                else:
                    error_message = f"❌ **Chart Generation Failed**\n\n" \
                                  f"Could not generate chart for {currency}.\n" \
                                  f"This might be due to:\n" \
                                  f"• No price data available for this time period\n" \
                                  f"• Network issues with data provider\n" \
                                  f"• Market was closed during this period\n" \
                                  f"• Try selecting a different time window"

                bot.edit_message_text(
                    error_message,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            bot.edit_message_text(
                f"❌ **Error Generating Chart**\n\n"
                f"An error occurred: {str(e)}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )

    def handle_multi_currency_selection(self, call: CallbackQuery, bot):
        """Handle multi-currency chart generation request."""
        # Answer callback query immediately to prevent timeout
        bot.answer_callback_query(call.id, "🔄 Setting up cross-rate chart...")

        # Parse callback data: viz_multi_CURRENCY_EVENTID_BEFOREHOURS_AFTERHOURS
        parts = call.data.split("_")
        primary_currency = parts[2]
        event_id = parts[3]
        before_hours = float(parts[4])
        after_hours = float(parts[5])

        # Get event details
        event = self._get_event_by_id(event_id)
        if not event:
            bot.edit_message_text(
                "❌ Event not found.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return

        # Create keyboard for secondary currency selection
        keyboard = []
        row = []

        for currency in self.available_currencies:
            if currency != primary_currency:  # Don't show the same currency twice
                row.append(InlineKeyboardButton(currency, callback_data=f"viz_secondary_{primary_currency}_{currency}_{event_id}_{before_hours}_{after_hours}"))
                if len(row) == 3:  # 3 buttons per row
                    keyboard.append(row)
                    row = []

        if row:  # Add remaining buttons
            keyboard.append(row)

        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Chart Options", callback_data=f"viz_event_{primary_currency}_{event_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            f"📊 **Cross-Rate Chart**\n\n"
            f"**Primary Currency:** {primary_currency}\n"
            f"**Event:** {event['event']}\n"
            f"**Date:** {event['date']} {event['time']}\n"
            f"**Time Window:** {before_hours}h before → {after_hours}h after\n\n"
            f"Select a secondary currency to create cross-rate chart:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def handle_secondary_currency_selection(self, call: CallbackQuery, bot):
        """Handle secondary currency selection for multi-currency chart."""
        # Answer callback query immediately to prevent timeout
        bot.answer_callback_query(call.id, "🔄 Generating cross-rate chart...")

        # Parse callback data: viz_secondary_PRIMARY_SECONDARY_EVENTID_BEFOREHOURS_AFTERHOURS
        parts = call.data.split("_")
        primary_currency = parts[2]
        secondary_currency = parts[3]
        event_id = parts[4]
        before_hours = float(parts[5])
        after_hours = float(parts[6])

        # Get event details
        event = self._get_event_by_id(event_id)
        if not event:
            bot.edit_message_text(
                "❌ Event not found.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            return

        # Clean event name for display
        clean_event_name = str(event['event']).replace('\\', '')

        # Show processing message
        bot.edit_message_text(
            f"🔄 Generating cross-rate chart...\n\n"
            f"Primary: {primary_currency}\n"
            f"Secondary: {secondary_currency}\n"
            f"Event: {clean_event_name}\n"
            f"Time window: {before_hours}h before → {after_hours}h after",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )

        try:
            # Generate the multi-currency chart with asymmetric time windows
            chart_buffer = self._generate_multi_currency_chart(event, primary_currency, secondary_currency, before_hours, after_hours)

            if chart_buffer:
                # Send the chart
                logger.info(f"Sending cross-rate chart for {primary_currency}/{secondary_currency} to user {call.from_user.id}")
                try:
                    bot.send_photo(
                        chat_id=call.from_user.id,
                        photo=chart_buffer,
                        caption=f"📊 **Cross-Rate Chart**\n\n"
                               f"**Pair:** {primary_currency}/{secondary_currency}\n"
                               f"**Event:** {clean_event_name}\n"
                               f"**Date:** {event['date']} {event['time']}\n"
                               f"**Time window:** {before_hours}h before → {after_hours}h after\n"
                               f"**Impact:** {event['impact_level']}",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Successfully sent cross-rate chart for {primary_currency}/{secondary_currency}")
                except Exception as send_error:
                    logger.error(f"Failed to send cross-rate chart: {send_error}")
                    # Try sending without markdown parsing
                    try:
                        bot.send_photo(
                            chat_id=call.from_user.id,
                            photo=chart_buffer,
                            caption=f"Cross-Rate Chart\n\nPair: {primary_currency}/{secondary_currency}\nEvent: {clean_event_name}\nDate: {event['date']} {event['time']}\nTime window: {before_hours}h before → {after_hours}h after\nImpact: {event['impact_level']}"
                        )
                        logger.info(f"Successfully sent cross-rate chart without markdown for {primary_currency}/{secondary_currency}")
                    except Exception as fallback_error:
                        logger.error(f"Failed to send cross-rate chart even without markdown: {fallback_error}")
                        raise send_error  # Re-raise original error

                # Show success message with options
                keyboard = [
                    [InlineKeyboardButton("📊 Generate Another Cross-Rate Chart", callback_data=f"viz_multi_{primary_currency}_{event_id}_{before_hours}_{after_hours}")],
                    [InlineKeyboardButton("📊 Generate Single Currency Chart", callback_data=f"viz_chart_{primary_currency}_{event_id}_1")],
                    [InlineKeyboardButton("🔙 Back to Events", callback_data=f"viz_currency_{primary_currency}")],
                    [InlineKeyboardButton("🏠 Back to Currencies", callback_data="viz_back_currencies")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                bot.edit_message_text(
                    f"✅ **Cross-Rate Chart Generated Successfully!**\n\n"
                    f"Chart showing {primary_currency}/{secondary_currency} has been sent.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                error_message = f"❌ **Cross-Rate Chart Generation Failed**\n\n" \
                              f"Could not generate chart for {primary_currency}/{secondary_currency}.\n" \
                              f"This might be due to:\n" \
                              f"• No price data available for the currency pair\n" \
                              f"• Network issues with data provider\n" \
                              f"• Market was closed during this period"

                bot.edit_message_text(
                    error_message,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error generating multi-currency chart: {e}")
            bot.edit_message_text(
                f"❌ **Error Generating Cross-Rate Chart**\n\n"
                f"An error occurred: {str(e)}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )

    def handle_back_to_currencies(self, call: CallbackQuery, bot):
        """Handle back to currencies button."""
        # Create currency selection keyboard
        keyboard = []
        row = []

        for currency in self.available_currencies:
            row.append(InlineKeyboardButton(currency, callback_data=f"viz_currency_{currency}"))
            if len(row) == 3:  # 3 buttons per row
                keyboard.append(row)
                row = []

        if row:  # Add remaining buttons
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            "📊 **Chart Visualization**\n\n"
            "Select a currency to view available events and generate charts:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    def _get_unique_events_for_currency(self, currency: str) -> List[str]:
        """Get unique event names for a specific currency from the database."""
        try:
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT DISTINCT event
                    FROM forex_news
                    WHERE currency = :currency
                    ORDER BY event
                """), {'currency': currency})

                unique_events = [row[0] for row in result]
                logger.info(f"Found {len(unique_events)} unique events for {currency}")
                return unique_events

        except Exception as e:
            logger.error(f"Error getting unique events for currency {currency}: {e}")
            return []

    def _get_events_for_currency(self, currency: str) -> List[Dict[str, Any]]:
        """Get events for a specific currency from the database."""
        try:
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, date, time, event, impact_level, actual, forecast, previous
                    FROM forex_news
                    WHERE currency = :currency
                    ORDER BY date DESC, time DESC
                    LIMIT 50
                """), {'currency': currency})

                events = []
                now = datetime.now()

                for row in result:
                    event_date = row[1]
                    event_time_str = row[2]

                    # Parse the full datetime
                    if event_date and event_time_str:
                        try:
                            event_datetime = datetime.strptime(f"{event_date.strftime('%Y-%m-%d')} {event_time_str}", "%Y-%m-%d %H:%M")
                            is_future = event_datetime > now
                        except ValueError:
                            is_future = False
                    else:
                        is_future = False

                    events.append({
                        'id': row[0],
                        'date': event_date.strftime('%Y-%m-%d') if event_date else '',
                        'time': event_time_str,
                        'event': row[3],
                        'impact_level': row[4],
                        'actual': row[5],
                        'forecast': row[6],
                        'previous': row[7],
                        'is_future': is_future
                    })

                return events
        except Exception as e:
            logger.error(f"Error getting events for currency {currency}: {e}")
            return []

    def _get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event details by ID."""
        try:
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, date, time, currency, event, impact_level, actual, forecast, previous
                    FROM forex_news
                    WHERE id = :event_id
                """), {'event_id': event_id})

                row = result.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'date': row[1].strftime('%Y-%m-%d') if row[1] else '',
                        'time': row[2],
                        'currency': row[3],
                        'event': row[4],
                        'impact_level': row[5],
                        'actual': row[6],
                        'forecast': row[7],
                        'previous': row[8]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting event by ID {event_id}: {e}")
            return None

    def _get_dates_for_event(self, currency: str, event_name: str) -> List[Dict[str, Any]]:
        """Get all dates for a specific event name and currency."""
        try:
            with self.db_service.db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, date, time, event, impact_level, actual, forecast, previous
                    FROM forex_news
                    WHERE currency = :currency AND event = :event_name
                    ORDER BY date DESC, time DESC
                """), {'currency': currency, 'event_name': event_name})

                events = []
                for row in result:
                    event_date = row[1]
                    now = datetime.now()

                    # Handle datetime comparison properly
                    if event_date:
                        if hasattr(event_date, 'date'):
                            # event_date is datetime.datetime, compare with date part
                            is_future = event_date.date() > now.date()
                        else:
                            # event_date is datetime.date, compare directly
                            is_future = event_date > now.date()
                    else:
                        is_future = False

                    events.append({
                        'id': row[0],
                        'date': event_date.strftime('%Y-%m-%d') if event_date else 'Unknown',
                        'time': row[2] or 'Unknown',
                        'event': row[3] or 'Unknown Event',
                        'impact_level': row[4] or 'medium',
                        'actual': row[5],
                        'forecast': row[6],
                        'previous': row[7],
                        'is_future': is_future
                    })

                logger.info(f"Found {len(events)} dates for event '{event_name}' in currency {currency}")
                return events

        except Exception as e:
            logger.error(f"Error getting dates for event '{event_name}' in currency {currency}: {e}")
            return []

    def _generate_event_chart(self, event: Dict[str, Any], currency: str, window_hours: float) -> Optional[BytesIO]:
        """Generate a chart for the specified event."""
        try:
            # Parse event date and time
            # Interpret DB times in display timezone to avoid UTC shifts
            import pytz
            tz = pytz.timezone(self.config.timezone)
            naive_dt = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
            event_date = tz.localize(naive_dt)

            # Generate the chart
            chart_buffer = chart_service.create_event_chart(
                currency=currency,
                event_time=event_date,
                window_hours=window_hours,
                event_name=event['event'],
                impact_level=event['impact_level']
            )

            return chart_buffer

        except Exception as e:
            logger.error(f"Error generating event chart: {e}")
            return None

    def _generate_multi_currency_chart(self, event: Dict[str, Any], primary_currency: str, secondary_currency: str, before_hours: float, after_hours: float) -> Optional[BytesIO]:
        """Generate a multi-currency chart for the specified event."""
        try:
            # Parse event date and time
            import pytz
            tz = pytz.timezone(self.config.timezone)
            naive_dt = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
            event_date = tz.localize(naive_dt)

            # Generate the multi-currency chart with asymmetric time windows
            chart_buffer = chart_service.create_multi_currency_chart(
                primary_currency=primary_currency,
                secondary_currency=secondary_currency,
                event_time=event_date,
                before_hours=before_hours,
                after_hours=after_hours,
                event_name=event['event'],
                impact_level=event['impact_level']
            )

            return chart_buffer

        except Exception as e:
            logger.error(f"Error generating multi-currency chart: {e}")
            return None

    def get_callback_handlers(self) -> Dict[str, callable]:
        """Get callback handlers for this module."""
        return {
            'viz_currency_': self.handle_currency_selection,
            'viz_events_': self.handle_events_page,
            'viz_event_': self.handle_event_selection,
            'viz_chart_': self.handle_chart_generation,
            'viz_multi_': self.handle_multi_currency_selection,
            'viz_secondary_': self.handle_secondary_currency_selection,
            'viz_back_currencies': self.handle_back_to_currencies,
        }
