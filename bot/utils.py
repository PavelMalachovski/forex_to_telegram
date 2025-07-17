import logging
from typing import Optional

logger = logging.getLogger(__name__)


def escape_markdown_v2(text: Optional[str]) -> str:
    """Escape special characters for Telegram MarkdownV2 format."""
    if not text:
        return "N/A"

    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def send_long_message(bot, chat_id: str, message: str):
    """Send long messages by splitting them into chunks."""
    if not bot or not message.strip():
        logger.error("Cannot send message: Bot not initialized or message is empty")
        return

    message = message.strip()
    while message:
        if len(message) <= 4096:
            part = message
            message = ""
        else:
            cut_pos = message[:4096].rfind('\n') if '\n' in message[:4096] else 4096
            part = message[:cut_pos].strip()
            message = message[cut_pos:].strip()

        if not part:
            logger.warning("Skipping empty message part")
            continue

        try:
            logger.info("Sending message part (length: %s)", len(part))
            bot.send_message(chat_id, part, parse_mode='MarkdownV2')
        except Exception:
            logger.exception("MarkdownV2 send failed. Falling back to plain text.")
            plain_part = part.replace('\\', '')
            bot.send_message(chat_id, plain_part)
