"""Bản UpdateStore và ContextStore trên Supabase. Đi qua db.client."""

from datetime import datetime, timezone

from config.settings import require_supabase
from core.telegram_channel import ClaimResult, StoredMessage
from db.client import (
    append_telegram_context,
    claim_telegram_update,
    list_telegram_context,
    mark_telegram_sent,
    postgrest_client,
    save_telegram_reply,
)


def _moment(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("mốc thời gian không đọc được")
    if parsed.tzinfo is None:
        raise ValueError("mốc thời gian không có timezone")
    return parsed.astimezone(timezone.utc)


def _optional_moment(value: object) -> datetime | None:
    if value is None:
        return None
    return _moment(value)


def _claim_result(data: dict) -> ClaimResult:
    return ClaimResult(
        inserted=data.get("inserted") is True,
        update_id=int(data["update_id"]),
        started_at=_moment(data["started_at"]),
        reply=data.get("reply") if isinstance(data.get("reply"), str) else None,
        sent_at=_optional_moment(data.get("sent_at")),
    )


def _message(data: object) -> StoredMessage:
    if not isinstance(data, dict):
        raise ValueError("Dòng ngữ cảnh không phải object.")
    return StoredMessage(
        saved_at=_moment(data["saved_at"]),
        role=str(data["role"]),
        body=str(data["body"]),
        update_id=int(data["update_id"]),
        chat_id=int(data["chat_id"]),
    )


class SupabaseTelegramChannel:
    """Một đối tượng cho cả bản ghi update và ngữ cảnh. Mỗi lời gọi mở client rồi đóng."""

    def __init__(self, source: object) -> None:
        self._url, self._key = require_supabase(source)

    async def claim(self, update_id: int, started_at: datetime) -> ClaimResult:
        async with postgrest_client(self._url, self._key) as client:
            data = await claim_telegram_update(client, update_id, started_at)
        return _claim_result(data)

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        async with postgrest_client(self._url, self._key) as client:
            return await save_telegram_reply(client, update_id, reply)

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        async with postgrest_client(self._url, self._key) as client:
            await mark_telegram_sent(client, update_id, sent_at)

    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        async with postgrest_client(self._url, self._key) as client:
            await append_telegram_context(client, update_id, role, chat_id, body, saved_at)

    async def list_recent(
        self,
        chat_id: int,
        saved_at_gte: datetime,
        limit: int,
    ) -> tuple[StoredMessage, ...]:
        async with postgrest_client(self._url, self._key) as client:
            rows = await list_telegram_context(client, chat_id, saved_at_gte, limit)
        return tuple(_message(row) for row in rows)
