"""Kho giả trong một đối tượng. Không có await giữa lúc thấy trống và lúc chèn."""

from dataclasses import dataclass
from datetime import datetime

from core.telegram_channel import ClaimResult, StoredMessage

_ROLES = frozenset({"user", "assistant"})


@dataclass
class _Update:
    started_at: datetime
    reply: str | None
    sent_at: datetime | None


class MemoryTelegramChannel:
    """Dict nằm trong đối tượng này. Không phải trạng thái production giữa hai request."""

    def __init__(self) -> None:
        self._updates: dict[int, _Update] = {}
        self._context: dict[tuple[int, str], StoredMessage] = {}

    async def claim(self, update_id: int, started_at: datetime) -> ClaimResult:
        row = self._updates.get(update_id)
        if row is None:
            row = _Update(started_at=started_at, reply=None, sent_at=None)
            self._updates[update_id] = row
            inserted = True
        else:
            inserted = False
        return ClaimResult(
            inserted=inserted,
            update_id=update_id,
            started_at=row.started_at,
            reply=row.reply,
            sent_at=row.sent_at,
        )

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        row = self._updates.get(update_id)
        if row is None or row.reply is not None:
            return False
        row.reply = reply
        return True

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        row = self._updates.get(update_id)
        if row is None or row.reply is None or row.sent_at is not None:
            return
        row.sent_at = sent_at

    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        if role not in _ROLES:
            raise ValueError(role)
        key = (update_id, role)
        if key in self._context:
            return
        self._context[key] = StoredMessage(
            saved_at=saved_at,
            role=role,
            body=body,
            update_id=update_id,
            chat_id=chat_id,
        )

    async def list_recent(
        self,
        chat_id: int,
        saved_at_gte: datetime,
        limit: int,
    ) -> tuple[StoredMessage, ...]:
        rows = [
            row
            for row in self._context.values()
            if row.chat_id == chat_id and row.saved_at >= saved_at_gte
        ]
        rows.sort(key=lambda row: (row.saved_at, row.role), reverse=True)
        return tuple(rows[:limit])
