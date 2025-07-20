import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)


def escape_markdown_v2(text: str) -> str:
    """Escape only Telegram MarkdownV2 special characters in user-supplied text."""
    # Only escape these characters in user input, not in the template
    escape_chars = r'[_*\[\]()~`>#+\-=|{}.!]'
    return re.sub(f'([{escape_chars}])', r'\\\1', text)


def send_long_message(bot, chat_id, text, parse_mode="MarkdownV2"):
    """Send a long message to Telegram, splitting if needed. Tries MarkdownV2, then HTML, then plain text."""
    max_length = 4096
    try:
        for i in range(0, len(text), max_length):
            bot.send_message(chat_id, text[i:i+max_length], parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"{parse_mode} send failed: {e}. Attempting to fix and retry.")
        # Try HTML fallback
        try:
            html_text = text.replace('**', '<b>').replace('__', '<i>').replace('`', '<code>')
            for i in range(0, len(html_text), max_length):
                bot.send_message(chat_id, html_text[i:i+max_length], parse_mode="HTML")
        except Exception as e2:
            logger.warning(f"HTML send failed: {e2}. Falling back to plain text.")
            for i in range(0, len(text), max_length):
                bot.send_message(chat_id, text[i:i+max_length])


def _fix_markdown_issues(text: str) -> str:
    """Attempt to fix common MarkdownV2 formatting issues."""
    # Remove any existing double escapes
    text = text.replace('\\\\\\\\', '\\\\')

    # Fix common problematic sequences
    problematic_sequences = {
        '\\.\\\\n': '\\.\n',  # Fix escaped periods before newlines
        '\\!\\\\n': '\\!\n',  # Fix escaped exclamations before newlines
        '\\-\\-': '\\-\\-',  # Ensure double dashes are properly escaped
    }

    for old, new in problematic_sequences.items():
        text = text.replace(old, new)

    return text


def _strip_markdown_escapes(text: str) -> str:
    """Remove all MarkdownV2 escape characters for plain text fallback."""
    # Remove escape characters but preserve the actual characters
    escape_chars = ['\\\\\\\\', '\\\\_', '\\\\*', '\\\\[', '\\\\]', '\\\\(', '\\\\)', '\\\\~', '\\\\`',
                   '\\\\>', '\\\\#', '\\\\+', '\\\\-', '\\\\=', '\\\\|', '\\\\{', '\\\\}', '\\\\.', '\\\\!']

    for escaped in escape_chars:
        # Remove the backslash but keep the character
        text = text.replace(escaped, escaped[1:])

    return text


def validate_markdown_v2(text: str) -> tuple[bool, str]:
    """Validate MarkdownV2 text and return validation result with error message."""
    try:
        # Check for unescaped special characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

        i = 0
        while i < len(text):
            char = text[i]
            if char == '\\':
                # Skip escaped character
                i += 2
                continue
            elif char in special_chars:
                return False, f"Unescaped special character '{char}' at position {i}"
            i += 1

        return True, "Valid MarkdownV2"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def safe_escape_markdown_v2(text: Optional[str]) -> str:
    """Safe version of escape_markdown_v2 with validation."""
    if not text or text.strip() == "":
        return "N/A"

    escaped = escape_markdown_v2(text)
    is_valid, error_msg = validate_markdown_v2(escaped)

    if not is_valid:
        logger.warning("MarkdownV2 validation failed for text '%s': %s", text[:50], error_msg)
        # Return a safe fallback
        return text.replace('\\', '\\\\').replace('_', '\\_').replace('*', '\\*')

    return escaped
