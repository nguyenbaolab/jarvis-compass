"""Lần chạy sáng trên đồ giả. Tiêm datetime, không đọc đồng hồ hệ thống."""

import asyncio
import json
from datetime import datetime, timezone

from core.morning import digest_update_id, render_digest
from core.plans import Subtask, SubtaskStatus
from core.telegram_channel import select_context, split_utf16
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.fakes.memory_telegram_channel import MemoryTelegramChannel
from scheduler.morning import run_morning

_KEYS = (
    "event",
    "outcome",
    "helsinki_date",
    "local_time",
    "update_id",
    "error_type",
    "error_code",
)
_SECRET_TITLE = "TIEU_DE_KHONG_VAO_LOG"
_WINTER_BEFORE = datetime(2026, 1, 15, 5, 59, tzinfo=timezone.utc)
_WINTER_EIGHT = datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc)
_SUMMER_EIGHT = datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc)


class CountingChannel(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.claims = 0
        self.marks = 0

    async def claim(self, update_id: int, started_at: datetime):
        self.claims += 1
        return await super().claim(update_id, started_at)

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        self.marks += 1
        await super().mark_sent(update_id, sent_at)


class RecordingSender:
    def __init__(self, fail_on: int | None = None) -> None:
        self.parts: list[tuple[int, str]] = []
        self.fail_on = fail_on
        self.attempts = 0

    async def send_part(self, chat_id: int, text: str) -> None:
        self.attempts += 1
        if self.fail_on is not None and self.attempts == self.fail_on:
            raise RuntimeError("send down")
        self.parts.append((chat_id, text))


def _owner(owner: str = "123") -> dict[str, str]:
    return {"TELEGRAM_OWNER_ID": owner}


async def _seed(store: MemoryPlanStore, goal: str, title: str) -> None:
    await store.add(goal, (Subtask(id="s", title=title, status=SubtaskStatus.PENDING, note=None),))


def _run(
    *,
    now: datetime,
    plans: MemoryPlanStore,
    channel: MemoryTelegramChannel,
    sender: RecordingSender,
    owner: str = "123",
) -> list[str]:
    lines: list[str] = []
    asyncio.run(
        run_morning(
            _owner(owner),
            now=now,
            plans=plans,
            channel=channel,
            sender=sender,
            log=lines.append,
        )
    )
    return lines


def _payload(line: str) -> dict[str, object]:
    loaded = json.loads(line)
    assert list(loaded) == list(_KEYS)
    return loaded


def test_before_eight_does_not_claim_send_or_mark() -> None:
    plans = MemoryPlanStore()
    channel = CountingChannel()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", _SECRET_TITLE)

    asyncio.run(prepare())
    lines = _run(now=_WINTER_BEFORE, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["event"] == "morning_digest"
    assert payload["outcome"] == "before_eight"
    assert payload["helsinki_date"] == "2026-01-15"
    assert payload["local_time"] == "07:59"
    assert payload["update_id"] == digest_update_id(datetime(2026, 1, 15).date())
    assert payload["update_id"] == -20260115
    assert payload["error_type"] is None
    assert payload["error_code"] is None
    assert _SECRET_TITLE not in lines[-1]
    assert channel.claims == 0
    assert channel.marks == 0
    assert sender.parts == []
    assert channel._updates == {}


def test_eight_sends_split_parts_in_order_then_marks() -> None:
    plans = MemoryPlanStore()
    channel = CountingChannel()
    sender = RecordingSender()
    title = "x" * 5000

    async def prepare() -> None:
        await _seed(plans, "Mục", title)

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    stored = asyncio.run(plans.list_newest_first())
    text = render_digest(stored)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "sent"
    assert payload["local_time"] == "08:00"
    assert payload["update_id"] == -20260115
    assert sender.parts == [(123, part) for part in split_utf16(text)]
    assert len(sender.parts) > 1
    assert channel.claims == 1
    assert channel.marks == 1
    assert channel._updates[-20260115].sent_at is not None


def test_summer_eight_uses_helsinki_not_utc() -> None:
    plans = MemoryPlanStore()
    channel = CountingChannel()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mùa hè", "một việc")

    asyncio.run(prepare())
    lines = _run(now=_SUMMER_EIGHT, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "sent"
    assert payload["helsinki_date"] == "2026-07-15"
    assert payload["local_time"] == "08:00"
    assert payload["update_id"] == -20260715
    assert sender.parts == [(123, "Mùa hè\nmột việc")]


def test_owner_id_that_is_not_a_decimal_integer_is_deferred() -> None:
    for owner in ("abc", " 123", "08"):
        plans = MemoryPlanStore()
        channel = CountingChannel()
        sender = RecordingSender()

        async def prepare() -> None:
            await _seed(plans, "Mục", "việc")

        asyncio.run(prepare())
        lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender, owner=owner)
        payload = _payload(lines[-1])
        assert payload["outcome"] == "deferred"
        assert payload["update_id"] == -20260115
        assert channel.claims == 0
        assert channel.marks == 0
        assert sender.parts == []


class FailAppendOnce(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.claims = 0
        self.marks = 0
        self.appends = 0
        self.left = 1

    async def claim(self, update_id: int, started_at: datetime):
        self.claims += 1
        return await super().claim(update_id, started_at)

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        self.marks += 1
        await super().mark_sent(update_id, sent_at)

    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        self.appends += 1
        if self.left:
            self.left -= 1
            raise RuntimeError("context")
        await super().append_once(update_id, role, chat_id, body, saved_at)


class ContextChannel(CountingChannel):
    def __init__(self, events: list[str] | None = None) -> None:
        super().__init__()
        self.appends = 0
        self.events = events

    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        self.appends += 1
        if self.events is not None:
            self.events.append("append")
        await super().append_once(update_id, role, chat_id, body, saved_at)

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        if self.events is not None:
            self.events.append("mark")
        await super().mark_sent(update_id, sent_at)


class EventSender(RecordingSender):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    async def send_part(self, chat_id: int, text: str) -> None:
        self.events.append("send")
        await super().send_part(chat_id, text)


def _roles(channel: MemoryTelegramChannel) -> list[str]:
    return [row.role for row in channel._context.values()]


def test_digest_writes_one_assistant_row_before_send() -> None:
    plans = MemoryPlanStore()
    events: list[str] = []
    channel = ContextChannel(events)
    sender = EventSender(events)

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc đầu")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    text = "Mục\nviệc đầu"
    assert _payload(lines[-1])["outcome"] == "sent"
    assert events == ["append", "send", "mark"]
    assert _roles(channel) == ["assistant"]
    stored = channel._context[(-20260115, "assistant")]
    assert stored.body == text
    assert stored.chat_id == 123
    assert channel._updates[-20260115].reply == text
    visible = select_context(
        asyncio.run(channel.list_recent(123, datetime(2026, 1, 1, tzinfo=timezone.utc), 20)),
        _WINTER_EIGHT,
    )
    assert [row.role for row in visible] == ["assistant"]
    assert visible[0].body == text


def test_context_write_error_does_not_send_or_mark() -> None:
    plans = MemoryPlanStore()
    channel = FailAppendOnce()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "RuntimeError"
    assert sender.parts == []
    assert channel.marks == 0
    assert channel._updates[-20260115].sent_at is None
    assert _roles(channel) == []


def test_existing_assistant_row_still_sends_without_a_second_row() -> None:
    plans = MemoryPlanStore()
    channel = ContextChannel()
    sender = RecordingSender()
    text = "Mục\nviệc"

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")
        await channel.append_once(-20260115, "assistant", 123, text, _WINTER_EIGHT)

    asyncio.run(prepare())
    before = channel.appends
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(lines[-1])["outcome"] == "sent"
    assert channel.appends == before + 1
    assert _roles(channel) == ["assistant"]
    assert channel._context[(-20260115, "assistant")].body == text
    assert sender.parts == [(123, text)]


def test_long_text_stays_one_context_string() -> None:
    plans = MemoryPlanStore()
    channel = ContextChannel()
    sender = RecordingSender()
    title = "y" * 5000

    async def prepare() -> None:
        await _seed(plans, "Mục", title)

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    stored = asyncio.run(plans.list_newest_first())
    text = render_digest(stored)
    assert _payload(lines[-1])["outcome"] == "sent"
    assert sender.parts == [(123, part) for part in split_utf16(text)]
    assert len(sender.parts) > 1
    assert _roles(channel) == ["assistant"]
    assert channel._context[(-20260115, "assistant")].body == text


class BoomPlans(MemoryPlanStore):
    async def list_newest_first(self) -> tuple:
        raise RuntimeError("kho kế hoạch")


class SaveFalse(ContextChannel):
    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        del update_id, reply
        return False


class FailSaveOnce(ContextChannel):
    def __init__(self) -> None:
        super().__init__()
        self.left = 1

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        if self.left:
            self.left -= 1
            raise RuntimeError("save down")
        return await super().save_reply_if_absent(update_id, reply)


class FailMarkOnce(ContextChannel):
    def __init__(self) -> None:
        super().__init__()
        self.left = 1

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        if self.left:
            self.left -= 1
            raise RuntimeError("mark down")
        await super().mark_sent(update_id, sent_at)


_NEXT_MORNING = datetime(2026, 1, 16, 6, 0, tzinfo=timezone.utc)


def test_stored_reply_is_resent_without_rebuilding_or_a_second_row() -> None:
    plans = BoomPlans()
    channel = ContextChannel()
    sender = RecordingSender()

    async def prepare() -> None:
        await channel.claim(-20260115, _WINTER_EIGHT)
        await channel.save_reply_if_absent(-20260115, "CHU_CU")
        await channel.append_once(-20260115, "assistant", 123, "CHU_CU", _WINTER_EIGHT)

    asyncio.run(prepare())
    before = channel.appends
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(lines[-1])["outcome"] == "resend"
    assert sender.parts == [(123, "CHU_CU")]
    assert channel.appends == before + 1
    assert _roles(channel) == ["assistant"]
    assert channel._context[(-20260115, "assistant")].body == "CHU_CU"
    assert channel.marks == 1


def test_send_error_leaves_sent_at_null() -> None:
    plans = MemoryPlanStore()
    channel = ContextChannel()
    sender = RecordingSender(fail_on=1)

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "RuntimeError"
    assert channel._updates[-20260115].sent_at is None
    assert channel.marks == 0
    assert sender.parts == []


def test_mark_error_defers_and_the_next_run_resends_stored_text() -> None:
    plans = MemoryPlanStore()
    channel = FailMarkOnce()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    first = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(first[-1])["outcome"] == "deferred"
    assert channel._updates[-20260115].sent_at is None
    assert channel._updates[-20260115].reply == "Mục\nviệc"
    sender.parts.clear()
    second = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(second[-1])["outcome"] == "resend"
    assert sender.parts == [(123, "Mục\nviệc")]
    assert channel._updates[-20260115].sent_at is not None
    assert _roles(channel) == ["assistant"]


def test_confirmed_day_does_not_send_again() -> None:
    plans = MemoryPlanStore()
    channel = ContextChannel()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    first = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(first[-1])["outcome"] == "sent"
    sent = len(sender.parts)
    second = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(second[-1])["outcome"] == "already_sent"
    assert len(sender.parts) == sent


def test_save_false_does_not_send_the_new_text() -> None:
    plans = MemoryPlanStore()
    channel = SaveFalse()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc mới")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert _payload(lines[-1])["outcome"] == "deferred"
    assert sender.parts == []
    assert channel.marks == 0
    assert _roles(channel) == []


def test_save_error_does_not_send_or_mark() -> None:
    plans = MemoryPlanStore()
    channel = FailSaveOnce()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "RuntimeError"
    assert sender.parts == []
    assert channel.marks == 0


def test_plan_read_error_does_not_build_or_mark() -> None:
    channel = ContextChannel()
    sender = RecordingSender()
    lines = _run(now=_WINTER_EIGHT, plans=BoomPlans(), channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "RuntimeError"
    assert sender.parts == []
    assert channel.marks == 0
    row = channel._updates[-20260115]
    assert row.reply is None
    assert row.sent_at is None


def test_next_helsinki_day_is_not_blocked_by_the_previous_marker() -> None:
    plans = MemoryPlanStore()
    channel = ContextChannel()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    sender.parts.clear()
    lines = _run(now=_NEXT_MORNING, plans=plans, channel=channel, sender=sender)
    payload = _payload(lines[-1])
    assert payload["outcome"] == "sent"
    assert payload["update_id"] == -20260116
    assert payload["helsinki_date"] == "2026-01-16"
    assert sender.parts == [(123, "Mục\nviệc")]
    assert channel._updates[-20260115].sent_at is not None
    assert channel._updates[-20260116].sent_at is not None


class FailClaim(CountingChannel):
    async def claim(self, update_id: int, started_at: datetime):
        self.claims += 1
        raise RuntimeError("claim down")


def test_claim_error_is_one_deferred_line() -> None:
    plans = MemoryPlanStore()
    channel = FailClaim()
    sender = RecordingSender()

    async def prepare() -> None:
        await _seed(plans, "Mục", "việc")

    asyncio.run(prepare())
    lines = _run(now=_WINTER_EIGHT, plans=plans, channel=channel, sender=sender)
    assert len(lines) == 1
    payload = _payload(lines[0])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "RuntimeError"
    assert sender.parts == []
    assert channel.marks == 0


def test_missing_supabase_url_is_one_deferred_line() -> None:
    lines: list[str] = []
    asyncio.run(
        run_morning(
            {"TELEGRAM_OWNER_ID": "123"},
            now=_WINTER_EIGHT,
            log=lines.append,
        )
    )
    assert len(lines) == 1
    payload = _payload(lines[0])
    assert payload["outcome"] == "deferred"
    assert payload["error_type"] == "SettingsError"

