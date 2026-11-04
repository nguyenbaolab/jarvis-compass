"""Luật thuần của kênh Telegram. Không gọi mạng, không đọc giờ hệ thống."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol

DEAD_AFTER = timedelta(seconds=90)
CONTEXT_WINDOW = timedelta(hours=24)
CONTEXT_LIMIT = 20


class Decision(Enum):
    Defer = "defer"
    Resend = "resend"
    SaveUncertain = "save_uncertain"
    Done = "done"


@dataclass(frozen=True)
class UpdateView:
    started_at: datetime
    reply: str | None
    sent_at: datetime | None


@dataclass(frozen=True)
class ClaimResult:
    inserted: bool
    update_id: int
    started_at: datetime
    reply: str | None
    sent_at: datetime | None


@dataclass(frozen=True)
class StoredMessage:
    saved_at: datetime
    role: str
    body: str
    update_id: int = 0
    chat_id: int = 0


class UpdateStore(Protocol):
    async def claim(self, update_id: int, started_at: datetime) -> ClaimResult:
        """Chèn nếu chưa có. Trả hàng và cờ inserted. Không đọc rồi ghi hai bước."""

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        """Ghi reply khi đang null. False khi không đổi được một hàng."""

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        """Đánh dấu đã gửi hết khi đã có câu và chưa có sent_at. Hàm SQL trả void."""


class ContextStore(Protocol):
    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        """Thêm một vai. Trùng (update_id, role) thì giữ thân cũ."""

    async def list_recent(
        self,
        chat_id: int,
        saved_at_gte: datetime,
        limit: int,
    ) -> tuple[StoredMessage, ...]:
        """Lọc theo mốc người gọi đưa. Không gọi now()."""


class TelegramSender(Protocol):
    async def send_part(self, chat_id: int, text: str) -> None:
        """Gửi một phần. Không tự chia câu."""


def split_utf16(text: str, limit: int = 4096) -> tuple[str, ...]:
    """Chia theo đơn vị UTF-16. Không cắt giữa một code point, không phần rỗng."""

    parts: list[str] = []
    current: list[str] = []
    units = 0
    for character in text:
        size = len(character.encode("utf-16-le")) // 2
        if current and units + size > limit:
            parts.append("".join(current))
            current = [character]
            units = size
        else:
            current.append(character)
            units += size
    if current:
        parts.append("".join(current))
    return tuple(parts)


def select_context(rows: Sequence[StoredMessage], now: datetime) -> tuple[StoredMessage, ...]:
    """Giữ saved_at >= now trừ 24 giờ, tối đa 20 tin mới nhất, rồi xếp cũ đến mới."""

    cutoff = now - CONTEXT_WINDOW
    fresh = [row for row in rows if row.saved_at >= cutoff]
    fresh.sort(key=lambda row: (row.saved_at, row.role), reverse=True)
    kept = fresh[:CONTEXT_LIMIT]
    kept.sort(key=lambda row: (row.saved_at, 0 if row.role == "user" else 1))
    return tuple(kept)


def decide_receive(record: UpdateView, now: datetime, dead_after: timedelta) -> Decision:
    """Done khi đã gửi hết. Resend khi đã có câu. Đúng khoảng chết vẫn là Hoãn."""

    if record.sent_at is not None:
        return Decision.Done
    if record.reply is not None:
        return Decision.Resend
    if now - record.started_at <= dead_after:
        return Decision.Defer
    return Decision.SaveUncertain
