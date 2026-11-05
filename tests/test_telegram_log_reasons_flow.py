"""Lý do defer và done của handle_update. Kho giả, không mở mạng."""

import asyncio
import json
from datetime import datetime, timedelta

import pytest

from api.telegram_update import Inbound, Outcome, handle_update
from core.telegram_channel import ClaimResult
from tests.test_telegram_update_flow import (
    BoomPlans,
    Clock,
    FailListRecent,
    GateModel,
    MemoryTelegramChannel,
    RecordingSender,
    ScriptModel,
    _CHAT,
    _START,
    _go,
    _reply,
)

_KEYS = {"outcome", "reason", "update_id", "error_type", "error_code"}
_TWO = {"resent", "already_sent", "uncertain_replied"}


class _SaveFalse(MemoryTelegramChannel):
    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        del update_id, reply
        return False


class _SaveFalseOnce(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.left = 1

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        if self.left:
            self.left -= 1
            return False
        return await super().save_reply_if_absent(update_id, reply)


class _OddReply(MemoryTelegramChannel):
    async def claim(self, update_id: int, started_at: datetime) -> ClaimResult:
        return ClaimResult(
            inserted=False,
            update_id=update_id,
            started_at=started_at,
            reply=0,  # type: ignore[arg-type]
            sent_at=None,
        )


def _outcome_lines(logs: list[str]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for line in logs:
        item = json.loads(line)
        if isinstance(item, dict) and "outcome" in item:
            found.append(item)
    return found


def _assert_channel(
    item: dict[str, object],
    outcome: str,
    reason: str,
    update_id: int,
    error_type: str | None = None,
    error_code: str | None = None,
) -> None:
    assert set(item) <= _KEYS
    keys = ["outcome", "reason", "update_id"]
    if error_type is not None:
        keys.append("error_type")
    if error_code is not None:
        keys.append("error_code")
    assert list(item) == keys
    assert item["outcome"] == outcome
    assert item["reason"] == reason
    assert item["update_id"] == update_id
    if error_type is None:
        assert "error_type" not in item
    else:
        assert item["error_type"] == error_type
    if error_code is None:
        assert "error_code" not in item
    else:
        assert item["error_code"] == error_code


async def _in_flight(update_id: int) -> list[str]:
    store = MemoryTelegramChannel()
    clock = Clock(_START)
    gate = GateModel()
    first = asyncio.create_task(
        _go(store, RecordingSender(), gate, clock, update_id, "đang chạy", log=None)
    )
    await gate.started.wait()
    logs: list[str] = []
    outcome = await _go(
        store,
        RecordingSender(),
        ScriptModel([_reply("không được", "end_turn")]),
        clock,
        update_id,
        "đang chạy",
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Defer
    gate.release.set()
    assert await first is Outcome.Done
    return logs


async def _store_unavailable(update_id: int) -> list[str]:
    async def open_channel() -> tuple[object, object]:
        raise RuntimeError("kho dong")

    logs: list[str] = []
    outcome = await handle_update(
        Inbound(update_id=update_id, chat_id=_CHAT, text="tin"),
        open_channel=open_channel,
        sender=RecordingSender(),
        plans=BoomPlans(),
        client=ScriptModel([_reply("không", "end_turn")]),
        api_key="caller-key",
        clock=Clock(_START),
        log=logs.append,
    )
    assert outcome is Outcome.Defer
    return logs


async def _reply_not_saved(update_id: int) -> list[str]:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = await _go(
        _SaveFalse(),
        sender,
        model,
        Clock(_START),
        update_id,
        None,
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    return logs


async def _context_failed(update_id: int) -> list[str]:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = await _go(
        FailListRecent(),
        sender,
        model,
        Clock(_START),
        update_id,
        "tin chu",
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    return logs


async def _send_failed(update_id: int) -> list[str]:
    """Gửi lại câu đã lưu mà _deliver lỗi. Đúng nhánh except của _resend."""

    store = MemoryTelegramChannel()
    await store.claim(update_id, _START)
    assert await store.save_reply_if_absent(update_id, "câu giữ") is True
    logs: list[str] = []
    sender = RecordingSender(fail_on=1)
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = await _go(
        store,
        sender,
        model,
        Clock(_START),
        update_id,
        "tin",
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    return logs


async def _unexpected(update_id: int) -> list[str]:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = await _go(
        _OddReply(),
        sender,
        model,
        Clock(_START),
        update_id,
        "tin",
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    return logs


async def _replied(update_id: int) -> list[str]:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("da gui", "end_turn")])
    outcome = await _go(
        MemoryTelegramChannel(),
        sender,
        model,
        Clock(_START),
        update_id,
        "tin chu",
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Done
    assert sender.parts == [(_CHAT, "da gui")]
    assert len(model.calls) == 1
    return logs


async def _resent(update_id: int) -> list[str]:
    store = MemoryTelegramChannel()
    sender = RecordingSender(fail_on=1)
    clock = Clock(_START)
    model = ScriptModel([_reply("câu gửi lại", "end_turn")])
    logs: list[str] = []
    first = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert first is Outcome.Defer
    assert sender.parts == []
    sender.fail_on = None
    clock.moment = _START + timedelta(seconds=1)
    second = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert second is Outcome.Done
    assert sender.parts == [(_CHAT, "câu gửi lại")]
    assert len(model.calls) == 1
    return logs


async def _already_sent(update_id: int) -> list[str]:
    store = MemoryTelegramChannel()
    sender = RecordingSender()
    clock = Clock(_START)
    model = ScriptModel([_reply("xong", "end_turn")])
    logs: list[str] = []
    first = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert first is Outcome.Done
    assert sender.parts == [(_CHAT, "xong")]
    clock.moment = _START + timedelta(seconds=1)
    second = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert second is Outcome.Done
    assert sender.parts == [(_CHAT, "xong")]
    assert len(model.calls) == 1
    return logs


async def _non_text(update_id: int) -> list[str]:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = await _go(
        MemoryTelegramChannel(),
        sender,
        model,
        Clock(_START),
        update_id,
        None,
        plans=BoomPlans(),
        log=logs,
    )
    assert outcome is Outcome.Done
    assert sender.parts == [(_CHAT, "Mình chỉ đọc được tin chữ.")]
    assert model.calls == []
    return logs


async def _uncertain_replied(update_id: int) -> list[str]:
    store = _SaveFalseOnce()
    sender = RecordingSender()
    clock = Clock(_START)
    model = ScriptModel([_reply("không", "end_turn")])
    logs: list[str] = []
    first = await _go(store, sender, model, clock, update_id, None, plans=BoomPlans(), log=logs)
    assert first is Outcome.Defer
    assert sender.parts == []
    clock.moment = _START + timedelta(seconds=91)
    second = await _go(store, sender, model, clock, update_id, None, plans=BoomPlans(), log=logs)
    assert second is Outcome.Done
    assert sender.parts == [(_CHAT, "Chưa chắc tin này đã được xử lý.")]
    assert model.calls == []
    return logs


_CASES = {
    "in_flight": _in_flight,
    "store_unavailable": _store_unavailable,
    "reply_not_saved": _reply_not_saved,
    "context_failed": _context_failed,
    "send_failed": _send_failed,
    "unexpected": _unexpected,
    "replied": _replied,
    "resent": _resent,
    "already_sent": _already_sent,
    "non_text": _non_text,
    "uncertain_replied": _uncertain_replied,
}


@pytest.mark.parametrize(
    ("reason", "outcome", "update_id", "error_type"),
    [
        pytest.param("in_flight", "defer", 301, None, id="in_flight"),
        pytest.param("store_unavailable", "defer", 302, "RuntimeError", id="store_unavailable"),
        pytest.param("reply_not_saved", "defer", 303, None, id="reply_not_saved"),
        pytest.param("context_failed", "defer", 304, "RuntimeError", id="context_failed"),
        pytest.param("send_failed", "defer", 305, "RuntimeError", id="send_failed"),
        pytest.param("unexpected", "defer", 306, None, id="unexpected"),
        pytest.param("replied", "done", 307, None, id="replied"),
        pytest.param("resent", "done", 308, None, id="resent"),
        pytest.param("already_sent", "done", 309, None, id="already_sent"),
        pytest.param("non_text", "done", 310, None, id="non_text"),
        pytest.param("uncertain_replied", "done", 311, None, id="uncertain_replied"),
    ],
)
def test_flow_log_reason(
    reason: str, outcome: str, update_id: int, error_type: str | None
) -> None:
    logs = asyncio.run(_CASES[reason](update_id))
    items = _outcome_lines(logs)
    assert len(items) == (2 if reason in _TWO else 1)
    _assert_channel(items[-1], outcome, reason, update_id, error_type)


async def _resent_from_saved_reply(update_id: int) -> list[str]:
    """Hai lần nhận khi câu đã lưu. Lần đầu _resend gửi lỗi, lần sau gửi lại."""

    store = MemoryTelegramChannel()
    await store.claim(update_id, _START)
    assert await store.save_reply_if_absent(update_id, "câu giữ") is True
    sender = RecordingSender(fail_on=1)
    clock = Clock(_START)
    model = ScriptModel([_reply("không", "end_turn")])
    logs: list[str] = []
    first = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert first is Outcome.Defer
    sender.fail_on = None
    clock.moment = _START + timedelta(seconds=1)
    second = await _go(store, sender, model, clock, update_id, "tin", plans=BoomPlans(), log=logs)
    assert second is Outcome.Done
    return logs


@pytest.mark.parametrize(
    ("case_id", "first_outcome", "first_reason", "update_id", "error_type"),
    [
        pytest.param("resent", "defer", "send_failed", 308, "RuntimeError", id="resent"),
        pytest.param("already_sent", "done", "replied", 309, None, id="already_sent"),
        pytest.param("uncertain_replied", "defer", "reply_not_saved", 311, None, id="uncertain_replied"),
    ],
)
def test_flow_first_line(
    case_id: str,
    first_outcome: str,
    first_reason: str,
    update_id: int,
    error_type: str | None,
) -> None:
    if case_id == "resent":
        logs = asyncio.run(_resent_from_saved_reply(update_id))
    else:
        logs = asyncio.run(_CASES[case_id](update_id))
    items = _outcome_lines(logs)
    _assert_channel(items[0], first_outcome, first_reason, update_id, error_type)


_LEAK = "boom secret-dung"
_FIXED_TEXT = "Mình chỉ đọc được tin chữ."


class LeakError(Exception):
    """Exception giả. Thông điệp chứa chuỗi giống secret và không được vào nhật ký."""


class _SaveRaises(MemoryTelegramChannel):
    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        del update_id, reply
        raise RuntimeError("save down")


class _MarkSentRaises(MemoryTelegramChannel):
    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        await super().mark_sent(update_id, sent_at)
        raise RuntimeError("mark sent")


class _MarkSentLeak(MemoryTelegramChannel):
    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        await super().mark_sent(update_id, sent_at)
        raise LeakError(_LEAK)


class _LeakList(MemoryTelegramChannel):
    async def list_recent(self, chat_id: int, saved_at_gte: datetime, limit: int) -> tuple:
        del chat_id, saved_at_gte, limit
        raise LeakError(_LEAK)


def _forbid_leak(logs: list[str]) -> None:
    assert _LEAK not in "\n".join(logs)


def test_reply_not_saved_when_save_raises() -> None:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = asyncio.run(
        _go(
            _SaveRaises(),
            sender,
            model,
            Clock(_START),
            312,
            None,
            plans=BoomPlans(),
            log=logs,
        )
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "reply_not_saved", 312, "RuntimeError")


def test_send_failed_when_mark_sent_raises() -> None:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = asyncio.run(
        _go(
            _MarkSentRaises(),
            sender,
            model,
            Clock(_START),
            313,
            None,
            plans=BoomPlans(),
            log=logs,
        )
    )
    assert outcome is Outcome.Defer
    assert sender.parts == [(_CHAT, _FIXED_TEXT)]
    assert model.calls == []
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "send_failed", 313, "RuntimeError")


def test_leak_store_unavailable() -> None:
    async def open_channel() -> tuple[object, object]:
        raise LeakError(_LEAK)

    logs: list[str] = []
    outcome = asyncio.run(
        handle_update(
            Inbound(update_id=314, chat_id=_CHAT, text="tin"),
            open_channel=open_channel,
            sender=RecordingSender(),
            plans=BoomPlans(),
            client=ScriptModel([_reply("không", "end_turn")]),
            api_key="caller-key",
            clock=Clock(_START),
            log=logs.append,
        )
    )
    assert outcome is Outcome.Defer
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "store_unavailable", 314, "LeakError")
    _forbid_leak(logs)


def test_leak_send_failed_mark_sent() -> None:
    async def scenario() -> list[str]:
        store = _MarkSentLeak()
        await store.claim(315, _START)
        assert await store.save_reply_if_absent(315, "câu giữ") is True
        logs: list[str] = []
        outcome = await _go(
            store,
            RecordingSender(),
            ScriptModel([_reply("không", "end_turn")]),
            Clock(_START),
            315,
            "tin",
            plans=BoomPlans(),
            log=logs,
        )
        assert outcome is Outcome.Defer
        return logs

    logs = asyncio.run(scenario())
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "send_failed", 315, "LeakError")
    _forbid_leak(logs)


def test_leak_context_failed() -> None:
    logs: list[str] = []
    sender = RecordingSender()
    model = ScriptModel([_reply("không", "end_turn")])
    outcome = asyncio.run(
        _go(
            _LeakList(),
            sender,
            model,
            Clock(_START),
            316,
            "tin chu",
            plans=BoomPlans(),
            log=logs,
        )
    )
    assert outcome is Outcome.Defer
    assert sender.parts == []
    assert model.calls == []
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "context_failed", 316, "LeakError")
    _forbid_leak(logs)
