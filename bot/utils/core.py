import logging
from typing import Optional

logger = logging.getLogger(__name__)


def escape_markdown_v2(text: Optional[str]) -> str:
    """Escape special characters for Telegram MarkdownV2 format."""
    if not text or text.strip() == "":
        return "N/A"
    
    text = str(text).strip()
    
    # Characters that need escaping in MarkdownV2
    special_chars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Escape each special character (backslash first to avoid double escaping)
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    
    return text


def send_long_message(bot, chat_id: str, message: str):
    """Send long messages by splitting them into chunks."""
    if not bot or not message.strip():
        logger.error("Cannot send message: Bot not initialized or message is empty")
        return

    message = message.strip()
    max_length = 4096
    
    while message:
        if len(message) <= max_length:
            part = message
            message = ""
        else:
            # Find a good break point (prefer newlines, then spaces)
            cut_pos = max_length
            for break_char in ['\n\n', '\n', ' ']:
                pos = message[:max_length].rfind(break_char)
                if pos > max_length * 0.8:  # Don't break too early
                    cut_pos = pos
                    break
            
            part = message[:cut_pos].strip()
            message = message[cut_pos:].strip()

        if not part:
            logger.warning("Skipping empty message part")
            continue

        try:
            logger.info("Sending message part (length: %s)", len(part))
            bot.send_message(chat_id, part, parse_mode='MarkdownV2')
        except Exception as e:
            logger.exception("MarkdownV2 send failed: %s. Falling back to plain text.", e)
            # Remove all escape characters for plain text
            plain_part = part.replace('\\', '')
            try:
                bot.send_message(chat_id, plain_part)
            except Exception as e2:
                logger.exception("Plain text send also failed: %s", e2)
