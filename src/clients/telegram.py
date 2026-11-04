"""Gửi một phần sendMessage. Không tự tách. Không phân loại lỗi vĩnh viễn."""

import logging

import httpx

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_TIMEOUT_SECONDS = 10.0


class TelegramSendError(Exception):
    """Gửi một phần thất bại. Thông điệp không chứa token."""


class TelegramSenderClient:
    """POST sendMessage với đúng chat_id và text."""

    def __init__(self, token: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = token
        self._transport = transport

    async def send_part(self, chat_id: int, text: str) -> None:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
                body = response.json()
        except Exception as error:
            del error
            raise TelegramSendError("Gửi không thành công.") from None
        if response.status_code < 200 or response.status_code >= 300:
            raise TelegramSendError("Gửi không thành công.")
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise TelegramSendError("Gửi không thành công.")
