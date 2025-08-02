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
        self.available_currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
        self.time_windows = [
            ("30min", 0.5),
            ("1h", 1),
            ("2h", 2),
            ("3h", 3)
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
        """Handle currency selection - show events for the selected currency."""
        currency = call.data.replace("viz_currency_", "")

        # Get events for this currency from the database
        events = self._get_events_for_currency(currency)

        if not events:
            bot.edit_message_text(
                f"❌ No events found for {currency}.\n\n"
                "Try selecting a different currency or check if there are events in the database.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)
            return

        # Create keyboard with events
        keyboard = []
        for event in events[:10]:  # Limit to 10 events to avoid keyboard size issues
            event_text = f"{event['date']} {event['time']} - {event['event'][:30]}..."
            callback_data = f"viz_event_{currency}_{event['id']}"
            keyboard.append([InlineKeyboardButton(event_text, callback_data=callback_data)])

        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Currencies", callback_data="viz_back_currencies")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            f"📈 **Events for {currency}**\n\n"
            f"Found {len(events)} events. Select an event to generate a chart:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    def handle_event_selection(self, call: CallbackQuery, bot):
        """Handle event selection - show time window options."""
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

        # Create keyboard with time window options
        keyboard = []
        for window_name, window_hours in self.time_windows:
            callback_data = f"viz_chart_{currency}_{event_id}_{window_hours}"
            keyboard.append([InlineKeyboardButton(f"📊 {window_name} window", callback_data=callback_data)])

        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Events", callback_data=f"viz_currency_{currency}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.edit_message_text(
            f"📊 **Generate Chart**\n\n"
            f"**Event:** {event['event']}\n"
            f"**Date:** {event['date']} {event['time']}\n"
            f"**Currency:** {currency}\n\n"
            "Select time window for the chart:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    def handle_chart_generation(self, call: CallbackQuery, bot):
        """Handle chart generation request."""
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
            bot.answer_callback_query(call.id)
            return

        # Show processing message
        bot.edit_message_text(
            f"🔄 Generating chart for {currency}...\n\n"
            f"Event: {event['event']}\n"
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
                bot.send_photo(
                    chat_id=call.from_user.id,
                    photo=chart_buffer,
                    caption=f"📊 **Chart for {currency}**\n\n"
                           f"**Event:** {event['event']}\n"
                           f"**Date:** {event['date']} {event['time']}\n"
                           f"**Time window:** ±{window_hours}h\n"
                           f"**Impact:** {event['impact_level']}",
                    parse_mode='Markdown'
                )

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
                bot.edit_message_text(
                    f"❌ **Chart Generation Failed**\n\n"
                    f"Could not generate chart for {currency}.\n"
                    f"This might be due to:\n"
                    f"• No price data available\n"
                    f"• Network issues\n"
                    f"• Invalid currency pair",
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

        bot.answer_callback_query(call.id)

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
                for row in result:
                    events.append({
                        'id': row[0],
                        'date': row[1].strftime('%Y-%m-%d') if row[1] else '',
                        'time': row[2],
                        'event': row[3],
                        'impact_level': row[4],
                        'actual': row[5],
                        'forecast': row[6],
                        'previous': row[7]
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

    def _generate_event_chart(self, event: Dict[str, Any], currency: str, window_hours: float) -> Optional[BytesIO]:
        """Generate a chart for the specified event."""
        try:
            # Parse event date and time
            event_date = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")

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

    def get_callback_handlers(self) -> Dict[str, callable]:
        """Get callback handlers for this module."""
        return {
            'viz_currency_': self.handle_currency_selection,
            'viz_event_': self.handle_event_selection,
            'viz_chart_': self.handle_chart_generation,
            'viz_back_currencies': self.handle_back_to_currencies,
        }
