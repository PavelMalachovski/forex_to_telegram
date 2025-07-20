import logging
from typing import Optional

logger = logging.getLogger(__name__)


def escape_markdown_v2(text: Optional[str]) -> str:
    """Fixed escape function for Telegram MarkdownV2 format."""
    if not text or text.strip() == "":
        return "N/A"
    
    text = str(text).strip()
    
    # Characters that need escaping in MarkdownV2
    # Order is critical: backslash must be escaped first to avoid double escaping
    special_chars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Escape backslash first to prevent double escaping
    text = text.replace('\\', '\\\\')
    
    # Then escape all other special characters
    for char in special_chars[1:]:  # Skip backslash since we already handled it
        text = text.replace(char, f"\\{char}")
    
    return text


def send_long_message(bot, chat_id: str, message: str):
    """Enhanced message sending with better error handling and fallback strategies."""
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
            for break_char in ['\\\\n\\\\n', '\\\\n', ' ']:
                pos = message[:max_length].rfind(break_char)
                if pos > max_length * 0.8:  # Don't break too early
                    cut_pos = pos
                    break
            
            part = message[:cut_pos].strip()
            message = message[cut_pos:].strip()

        if not part:
            logger.warning("Skipping empty message part")
            continue

        # Try sending with MarkdownV2 first
        success = False
        try:
            logger.info("Sending message part (length: %s)", len(part))
            bot.send_message(chat_id, part, parse_mode='MarkdownV2')
            success = True
        except Exception as e:
            logger.warning("MarkdownV2 send failed: %s. Attempting to fix and retry.", e)
            
            # Try to fix common MarkdownV2 issues and retry
            try:
                fixed_part = _fix_markdown_issues(part)
                bot.send_message(chat_id, fixed_part, parse_mode='MarkdownV2')
                success = True
                logger.info("Successfully sent after fixing MarkdownV2 issues")
            except Exception as e2:
                logger.warning("Fixed MarkdownV2 also failed: %s. Falling back to plain text.", e2)
        
        # Fallback to plain text if MarkdownV2 fails
        if not success:
            try:
                # Remove all escape characters for plain text
                plain_part = _strip_markdown_escapes(part)
                bot.send_message(chat_id, plain_part)
                logger.info("Successfully sent as plain text")
            except Exception as e3:
                logger.error("Plain text send also failed: %s", e3)


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