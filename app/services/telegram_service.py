"""Telegram service implementation."""

from typing import Optional, Dict, Any
import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import TelegramError
from app.models.telegram import TelegramUpdate

logger = structlog.get_logger(__name__)


class TelegramService:
    """Telegram bot service."""

    def __init__(self):
        self.bot_token = settings.telegram.bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.webhook_url = settings.telegram.webhook_url
        self.webhook_secret = settings.telegram.webhook_secret

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a message to a chat."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }

                if reply_markup:
                    payload["reply_markup"] = reply_markup

                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info("Message sent successfully", chat_id=chat_id)
                    return True
                else:
                    logger.error("Failed to send message", chat_id=chat_id, status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to send message", chat_id=chat_id, error=str(e), exc_info=True)
            raise TelegramError(f"Failed to send message: {e}")

    async def send_photo(
        self,
        chat_id: int,
        photo: bytes,
        caption: Optional[str] = None
    ) -> bool:
        """Send a photo to a chat."""
        try:
            async with httpx.AsyncClient() as client:
                files = {"photo": ("chart.png", photo, "image/png")}
                data = {"chat_id": chat_id}

                if caption:
                    data["caption"] = caption

                response = await client.post(
                    f"{self.base_url}/sendPhoto",
                    data=data,
                    files=files,
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info("Photo sent successfully", chat_id=chat_id)
                    return True
                else:
                    logger.error("Failed to send photo", chat_id=chat_id, status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to send photo", chat_id=chat_id, error=str(e), exc_info=True)
            raise TelegramError(f"Failed to send photo: {e}")

    async def send_document(
        self,
        chat_id: int,
        document: bytes,
        filename: str,
        caption: Optional[str] = None
    ) -> bool:
        """Send a document to a chat."""
        try:
            async with httpx.AsyncClient() as client:
                files = {"document": (filename, document, "application/octet-stream")}
                data = {"chat_id": chat_id}

                if caption:
                    data["caption"] = caption

                response = await client.post(
                    f"{self.base_url}/sendDocument",
                    data=data,
                    files=files,
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info("Document sent successfully", chat_id=chat_id, filename=filename)
                    return True
                else:
                    logger.error("Failed to send document", chat_id=chat_id, filename=filename, status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to send document", chat_id=chat_id, filename=filename, error=str(e), exc_info=True)
            raise TelegramError(f"Failed to send document: {e}")

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get webhook information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/getWebhookInfo", timeout=10.0)

                if response.status_code == 200:
                    return response.json()
                else:
                    raise TelegramError(f"Failed to get webhook info: {response.text}")

        except Exception as e:
            logger.error("Failed to get webhook info", error=str(e), exc_info=True)
            raise TelegramError(f"Failed to get webhook info: {e}")

    async def set_webhook(self, url: str, secret_token: Optional[str] = None) -> bool:
        """Set webhook URL."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {"url": url}

                if secret_token:
                    payload["secret_token"] = secret_token

                response = await client.post(
                    f"{self.base_url}/setWebhook",
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Webhook set successfully", url=url)
                        return True
                    else:
                        logger.error("Failed to set webhook", url=url, result=result)
                        return False
                else:
                    logger.error("Failed to set webhook", url=url, status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to set webhook", url=url, error=str(e), exc_info=True)
            raise TelegramError(f"Failed to set webhook: {e}")

    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/deleteWebhook", timeout=10.0)

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Webhook deleted successfully")
                        return True
                    else:
                        logger.error("Failed to delete webhook", result=result)
                        return False
                else:
                    logger.error("Failed to delete webhook", status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to delete webhook", error=str(e), exc_info=True)
            raise TelegramError(f"Failed to delete webhook: {e}")

    async def get_me(self) -> Dict[str, Any]:
        """Get bot information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/getMe", timeout=10.0)

                if response.status_code == 200:
                    return response.json()
                else:
                    raise TelegramError(f"Failed to get bot info: {response.text}")

        except Exception as e:
            logger.error("Failed to get bot info", error=str(e), exc_info=True)
            raise TelegramError(f"Failed to get bot info: {e}")

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """Answer a callback query."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "callback_query_id": callback_query_id,
                    "show_alert": show_alert
                }

                if text:
                    payload["text"] = text

                response = await client.post(
                    f"{self.base_url}/answerCallbackQuery",
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Callback query answered successfully", callback_query_id=callback_query_id)
                        return True
                    else:
                        logger.error("Failed to answer callback query", callback_query_id=callback_query_id, result=result)
                        return False
                else:
                    logger.error("Failed to answer callback query", callback_query_id=callback_query_id, status_code=response.status_code, response=response.text)
                    return False

        except Exception as e:
            logger.error("Failed to answer callback query", callback_query_id=callback_query_id, error=str(e), exc_info=True)
            raise TelegramError(f"Failed to answer callback query: {e}")

    def validate_webhook_secret(self, received_secret: str) -> bool:
        """Validate webhook secret token."""
        if not self.webhook_secret:
            return True  # No secret configured

        return received_secret == self.webhook_secret
