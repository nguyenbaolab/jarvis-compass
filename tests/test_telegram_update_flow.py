"""Luồng handle_update trên kho giả. Không mở mạng. Không ngủ thật."""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from core.llm import ModelResponse, ToolRequest
from core.telegram_channel import split_utf16
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.fakes.memory_telegram_channel import MemoryTelegramChannel

_START = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_CHAT = 7
_FIXED = "Mình chỉ đọc được tin chữ."
_UNCERTAIN = "Chưa chắc tin này đã được xử lý."
_D021 = "Chưa chắc thay đổi đã được lưu."
_COMPOSED = "1. Đã lưu kế hoạch Học tiếng Nhật."
_COMPOSED_MULTI = (
    "1. Đã lưu kế hoạch Học tiếng Nhật.\n"
    "Chưa chắc thay đổi đã được lưu.\n"
    "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."
)
_SECRET = "webhook-secret-khong-log"


def _reply(text: str, stop_reason: str | None, tools: tuple[ToolRequest, ...] = ()) -> ModelResponse:
    return ModelResponse(
        text=text,
        tool_requests=tools,
        stop_reason=stop_reason,
        input_tokens=1,
        output_tokens=1,
        model="scripted",
    )


def _tool(tool_id: str, name: str, tool_input: dict[str, object]) -> ToolRequest:
    return ToolRequest(id=tool_id, name=name, tool_input=tool_input)


def _create() -> ModelResponse:
    return _reply("", "tool_use", (_tool("t-create", "create_plan", {"goal": "Học tiếng Nhật"}),))


class Clock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment


class ScriptModel:
    def __init__(self, steps: list[object]) -> None:
        self._steps = list(steps)
        self.calls: list[object] = []
        self.model = "scripted"

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del api_key, timeout
        self.calls.append(request)
        item = self._steps.pop(0)
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, ModelResponse)
        return item


class GateModel:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls: list[object] = []
        self.model = "gate"

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del api_key, timeout
        self.calls.append(request)
        self.started.set()
        await self.release.wait()
        return _reply("xong", "end_turn")


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


class BoomPlans(MemoryPlanStore):
    async def add(self, goal: str, subtasks: tuple) -> object:
        raise AssertionError("kho kế hoạch")

    async def list_newest_first(self) -> tuple:
        raise AssertionError("kho kế hoạch")

    async def get(self, plan_id: str) -> object:
        raise AssertionError("kho kế hoạch")

    async def replace(self, plan: object) -> None:
        raise AssertionError("kho kế hoạch")


class HangPlans(MemoryPlanStore):
    async def list_newest_first(self) -> tuple:
        await asyncio.Event().wait()
        raise AssertionError("không trả")


class FailSaveOnce(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.left = 1

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        if self.left:
            self.left -= 1
            raise RuntimeError("save down")
        return await super().save_reply_if_absent(update_id, reply)


class FailAppendOnce(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.left = 1

    async def append_once(self, update_id: int, role: str, chat_id: int, body: str, saved_at: datetime) -> None:
        if self.left:
            self.left -= 1
            raise RuntimeError("context")
        await super().append_once(update_id, role, chat_id, body, saved_at)


class FailAppend(MemoryTelegramChannel):
    async def append_once(self, update_id: int, role: str, chat_id: int, body: str, saved_at: datetime) -> None:
        raise RuntimeError("context")


class FailListRecent(MemoryTelegramChannel):
    def __init__(self) -> None:
        super().__init__()
        self.fail = True

    async def list_recent(self, chat_id: int, saved_at_gte: datetime, limit: int) -> tuple:
        if self.fail:
            raise RuntimeError("đọc ngữ cảnh")
        return await super().list_recent(chat_id, saved_at_gte, limit)


def _open(store: MemoryTelegramChannel):
    async def open_channel():
        return store, store

    return open_channel


def _texts(request: object) -> list[tuple[str, str]]:
    return [(message.role, message.text) for message in request.messages]


async def _go(
    store: MemoryTelegramChannel,
    sender: RecordingSender,
    model: object,
    clock: Clock,
    update_id: int,
    text: str | None,
    *,
    plans: MemoryPlanStore | None = None,
    api_key: str | None = "caller-key",
    log: list[str] | None = None,
):
    from api.telegram_update import Inbound, handle_update

    return await handle_update(
        Inbound(update_id=update_id, chat_id=_CHAT, text=text),
        open_channel=_open(store),
        sender=sender,
        plans=MemoryPlanStore() if plans is None else plans,
        client=model,
        api_key=api_key,
        clock=clock,
        log=None if log is None else log.append,
    )


def test_owner_text_sends_one_plain_sentence() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        sentence = "một *hai* _ba_ `bon`"
        model = ScriptModel([_reply(sentence, "end_turn"), _reply("bắt đầu", "end_turn")])
        done = await _go(store, sender, model, clock, 1, sentence, plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, sentence)]
        clock.moment = _START + timedelta(seconds=1)
        await _go(store, sender, model, clock, 2, "/start", plans=BoomPlans())
        assert sender.parts == [(_CHAT, sentence), (_CHAT, "bắt đầu")]

    asyncio.run(scenario())


def test_overlap_while_running_defers() -> None:
    from api.telegram_update import Inbound, Outcome, handle_update

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        gate = GateModel()
        inbound = Inbound(update_id=3, chat_id=_CHAT, text="đang chạy")
        first = asyncio.create_task(
            handle_update(
                inbound,
                open_channel=_open(store),
                sender=sender,
                plans=MemoryPlanStore(),
                client=gate,
                api_key="caller-key",
                clock=clock,
            )
        )
        await gate.started.wait()
        other = ScriptModel([_reply("không được", "end_turn")])
        second = await handle_update(
            inbound,
            open_channel=_open(store),
            sender=RecordingSender(),
            plans=BoomPlans(),
            client=other,
            api_key="caller-key",
            clock=clock,
        )
        assert second is Outcome.Defer
        assert other.calls == []
        assert (await store.claim(3, _START)).reply is None
        gate.release.set()
        assert await first is Outcome.Done

    asyncio.run(scenario())


def test_unexpected_exception_saves_uncertain_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.telegram_update import Outcome

    async def _boom(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("lỗi nội bộ")

    monkeypatch.setattr("api.telegram_update.run_turn", _boom)

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("không", "end_turn")])
        done = await _go(store, sender, model, clock, 4, "tin lỗi", plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, _UNCERTAIN)]
        assert "RuntimeError" not in sender.parts[0][1]
        assert "lỗi nội bộ" not in sender.parts[0][1]
        rows = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert {row.body for row in rows} == {"tin lỗi", _UNCERTAIN}
        monkeypatch.undo()
        cancelled = ScriptModel([asyncio.CancelledError()])
        with pytest.raises(asyncio.CancelledError):
            await _go(store, RecordingSender(), cancelled, clock, 5, "tin huỷ")
        assert (await store.claim(5, _START)).reply is None

    asyncio.run(scenario())


def test_save_reply_failure_defers_then_uncertain() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = FailSaveOnce()
        sender = RecordingSender()
        clock = Clock(_START)
        plans = MemoryPlanStore()
        model = ScriptModel([_create(), _reply("xong", "end_turn")])
        deferred = await _go(store, sender, model, clock, 6, "lập", plans=plans)
        assert deferred is Outcome.Defer
        assert sender.parts == []
        assert len(await plans.list_newest_first()) == 1
        assert len(model.calls) == 2
        clock.moment = _START + timedelta(seconds=91)
        later = await _go(store, sender, model, clock, 6, "lập", plans=plans)
        assert later is Outcome.Done
        assert sender.parts == [(_CHAT, _UNCERTAIN)]
        assert len(model.calls) == 2
        assert len(await plans.list_newest_first()) == 1

    asyncio.run(scenario())


def test_context_write_failure_sends_nothing() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = FailAppend()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("câu đã chốt", "end_turn")])
        deferred = await _go(store, sender, model, clock, 7, "tin", plans=BoomPlans())
        assert deferred is Outcome.Defer
        assert sender.parts == []
        assert len(model.calls) == 1
        assert (await store.claim(7, _START)).reply == "câu đã chốt"

    asyncio.run(scenario())


def test_next_receive_writes_both_roles_then_sends_saved() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = FailAppendOnce()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("câu đã lưu", "end_turn")])
        await _go(store, sender, model, clock, 8, "tin gốc", plans=BoomPlans())
        assert sender.parts == []
        clock.moment = _START + timedelta(seconds=1)
        done = await _go(store, sender, model, clock, 8, "tin gốc", plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, "câu đã lưu")]
        assert len(model.calls) == 1
        rows = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert {(row.role, row.body) for row in rows} == {("user", "tin gốc"), ("assistant", "câu đã lưu")}

    asyncio.run(scenario())


def test_resend_does_not_duplicate_context() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender(fail_on=1)
        clock = Clock(_START)
        model = ScriptModel([_reply("câu gửi lại", "end_turn")])
        deferred = await _go(store, sender, model, clock, 9, "tin", plans=BoomPlans())
        assert deferred is Outcome.Defer
        before = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        sender.fail_on = None
        clock.moment = _START + timedelta(seconds=1)
        await _go(store, sender, model, clock, 9, "tin", plans=BoomPlans())
        after = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert {(row.role, row.body) for row in after} == {(row.role, row.body) for row in before}
        assert len(after) == 2
        assert len(model.calls) == 1
        assert sender.parts == [(_CHAT, "câu gửi lại")]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "case_id",
    [
        "voice",
        "photo",
        "file",
        "captioned_photo",
        "sticker",
        "location",
        "contact",
        "poll",
        "empty_text",
        "whitespace_text",
    ],
)
def test_non_text_fixed_sentence_skips_context(case_id: str) -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("không", "end_turn")])
        text = {"empty_text": "", "whitespace_text": "   "}.get(case_id)
        await _go(store, sender, model, clock, 10, text, plans=BoomPlans())
        assert sender.parts == [(_CHAT, _FIXED)]
        assert model.calls == []
        assert await store.list_recent(_CHAT, _START - timedelta(hours=1), 20) == ()

    asyncio.run(scenario())


def test_hung_plan_store_stays_inside_turn_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = {"n": 0}

    def _clock() -> float:
        ticks["n"] += 1
        if ticks["n"] < 6:
            return 0.0
        return 19.9 + (ticks["n"] - 6) * 0.001

    monkeypatch.setattr("turns.llm_turn._now", _clock)

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        logs: list[str] = []
        model = ScriptModel([_reply("", "tool_use", (_tool("t1", "get_plans", {}),)), _reply("đã xong", "end_turn")])
        await asyncio.wait_for(
            _go(store, sender, model, clock, 11, _SECRET, plans=HangPlans(), api_key="khoa-api-khac-han-chuoi", log=logs),
            timeout=2,
        )
        assert sender.parts == [(_CHAT, "đã xong")]
        blob = "\n".join(logs)
        assert "khoa-api-khac-han-chuoi" not in blob
        assert _SECRET not in blob

    asyncio.run(scenario())


def test_store_down_at_receive_defers() -> None:
    from api.telegram_update import Inbound, Outcome, handle_update
    from config.settings import SettingsError

    async def open_channel():
        raise SettingsError("Thiếu SUPABASE_URL.")

    async def scenario() -> None:
        model = ScriptModel([_reply("không", "end_turn")])
        sender = RecordingSender()
        result = await handle_update(
            Inbound(update_id=12, chat_id=_CHAT, text="tin"),
            open_channel=open_channel,
            sender=sender,
            plans=BoomPlans(),
            client=model,
            api_key="caller-key",
            clock=Clock(_START),
        )
        assert result is Outcome.Defer
        assert model.calls == []
        assert sender.parts == []

    asyncio.run(scenario())


def test_missing_key_saves_sentence_without_key_value() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("không gọi", "end_turn")])
        done = await _go(store, sender, model, clock, 13, "tin", api_key=None, plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, "Thiếu ANTHROPIC_API_KEY.")]
        assert (await store.claim(13, _START)).reply == "Thiếu ANTHROPIC_API_KEY."
        assert model.calls == []
        blocked = FailAppend()
        quiet = RecordingSender()
        deferred = await _go(blocked, quiet, model, clock, 14, "tin nữa", api_key=None)
        assert deferred is Outcome.Defer
        assert quiet.parts == []

    asyncio.run(scenario())


def test_partial_send_retries_whole_sentence() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender(fail_on=2)
        clock = Clock(_START)
        sentence = "a" * 4096 + "b"
        model = ScriptModel([_reply(sentence, "end_turn")])
        deferred = await _go(store, sender, model, clock, 15, "tin dài", plans=BoomPlans())
        assert deferred is Outcome.Defer
        assert (await store.claim(15, _START)).sent_at is None
        assert (await store.claim(15, _START)).reply == sentence
        assert len(model.calls) == 1
        clock.moment = _START + timedelta(seconds=1)
        retry = RecordingSender()
        await _go(store, retry, model, clock, 15, "tin dài", plans=BoomPlans())
        assert retry.parts == [(_CHAT, part) for part in split_utf16(sentence)]
        assert len(model.calls) == 1

    asyncio.run(scenario())


def test_yes_after_bot_question_sees_the_question() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        saved = _START - timedelta(hours=1)
        await store.claim(20, saved)
        await store.append_once(20, "assistant", _CHAT, "Bạn muốn mình lập kế hoạch không?", saved)
        model = ScriptModel([_reply("được", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 21, "có")
        assert _texts(model.calls[0]) == [
            ("assistant", "Bạn muốn mình lập kế hoạch không?"),
            ("user", "có"),
        ]

    asyncio.run(scenario())


def test_only_20_newest_stored_messages_reach_model() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        for index in range(25):
            update_id = 100 + index
            saved = _START - timedelta(minutes=25 - index)
            await store.claim(update_id, saved)
            await store.append_once(update_id, "user", _CHAT, f"m{index}", saved)
        model = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 200, "tin mới")
        assert _texts(model.calls[0]) == [("user", f"m{index}") for index in range(5, 25)] + [("user", "tin mới")]
        assert len(model.calls[0].messages) == 21

    asyncio.run(scenario())


def test_stored_message_older_than_24h_is_not_sent_to_model() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        saved = _START - timedelta(hours=24, seconds=1)
        await store.claim(30, saved)
        await store.append_once(30, "user", _CHAT, "cũ", saved)
        model = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 31, "mới")
        assert _texts(model.calls[0]) == [("user", "mới")]

    asyncio.run(scenario())


def test_stored_message_at_exactly_24h_is_sent_to_model() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        saved = _START - timedelta(hours=24)
        await store.claim(32, saved)
        await store.append_once(32, "user", _CHAT, "đúng", saved)
        model = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 33, "mới")
        assert _texts(model.calls[0]) == [("user", "đúng"), ("user", "mới")]

    asyncio.run(scenario())


def test_fresh_handler_same_store_sees_previous_pair() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        first_model = ScriptModel([_reply("trả lời một", "end_turn")])
        await _go(store, RecordingSender(), first_model, clock, 40, "tin một")
        clock.moment = _START + timedelta(seconds=1)
        second_model = ScriptModel([_reply("trả lời hai", "end_turn")])
        await _go(store, RecordingSender(), second_model, clock, 41, "tin hai")
        assert _texts(second_model.calls[0]) == [
            ("user", "tin một"),
            ("assistant", "trả lời một"),
            ("user", "tin hai"),
        ]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("case_id", "sentence", "steps"),
    [
        ("empty_text", "Mình chưa có câu trả lời cho tin này.", [_reply("", "end_turn")]),
        ("whitespace_text", "Mình chưa có câu trả lời cho tin này.", [_reply("   ", "end_turn")]),
        ("max_tokens", "Câu trả lời bị cắt vì quá dài.", [_reply("dở", "max_tokens")]),
        ("refusal", "Mình không trả lời được tin này.", [_reply("", "refusal")]),
        ("model_error", "Chưa liên lạc được để trả lời lúc này.", [RuntimeError("boom")]),
        ("budget_exhausted", "Chưa liên lạc được để trả lời lúc này.", [_reply("không tới", "end_turn")]),
        (
            "three_rounds_exhausted",
            "Chưa trả lời xong yêu cầu này.",
            [_reply("", "tool_use", (_tool(f"t{index}", "get_plans", {}),)) for index in range(4)],
        ),
    ],
)
def test_fixed_sentence_reaches_owner(
    case_id: str,
    sentence: str,
    steps: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if case_id == "budget_exhausted":
        marks = iter((0.0, 21.0, 21.0, 21.0, 21.0))
        monkeypatch.setattr("turns.llm_turn._now", lambda: next(marks))

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        plans = MemoryPlanStore() if case_id == "three_rounds_exhausted" else BoomPlans()
        model = ScriptModel(steps)
        await _go(store, sender, model, Clock(_START), 50, "tin", plans=plans)
        assert sender.parts == [(_CHAT, sentence)]
        assert (await store.claim(50, _START)).reply == sentence

    asyncio.run(scenario())


@pytest.mark.parametrize("case_id", ["max_tokens", "refusal"])
def test_composed_reply_wins_over_max_tokens_and_refusal(case_id: str) -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        model = ScriptModel([_create(), _reply("", case_id)])
        await _go(store, sender, model, Clock(_START), 51, "lập", plans=MemoryPlanStore())
        assert sender.parts == [(_CHAT, _COMPOSED)]

    asyncio.run(scenario())


def test_one_turn_one_plan_one_reply_then_done() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        plans = MemoryPlanStore()
        model = ScriptModel([_create(), _reply("xong một câu", "end_turn")])
        clock = Clock(_START)
        await _go(store, sender, model, clock, 52, "lập", plans=plans)
        assert len(model.calls) == 2
        assert len(await plans.list_newest_first()) == 1
        assert sender.parts == [(_CHAT, "xong một câu")]
        assert (await store.claim(52, _START)).sent_at is not None
        clock.moment = _START + timedelta(seconds=1)
        await _go(store, sender, model, clock, 52, "lập", plans=plans)
        assert len(model.calls) == 2
        assert len(await plans.list_newest_first()) == 1
        assert sender.parts == [(_CHAT, "xong một câu")]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("case_id", "sentence"),
    [("d021_sentence", _D021), ("composed_multiline", _COMPOSED_MULTI)],
)
def test_resend_sends_saved_text_exactly(case_id: str, sentence: str) -> None:
    del case_id

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        await store.claim(53, _START)
        assert await store.save_reply_if_absent(53, sentence) is True
        sender = RecordingSender()
        model = ScriptModel([_reply("không", "end_turn")])
        await _go(store, sender, model, Clock(_START), 53, "tin gốc", plans=BoomPlans())
        assert sender.parts == [(_CHAT, sentence)]
        assert model.calls == []

    asyncio.run(scenario())


def test_different_update_ids_same_text_are_two_turns() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        model = ScriptModel([_reply("một", "end_turn"), _reply("hai", "end_turn")])
        clock = Clock(_START)
        await _go(store, RecordingSender(), model, clock, 60, "cùng chữ")
        clock.moment = _START + timedelta(seconds=1)
        await _go(store, RecordingSender(), model, clock, 61, "cùng chữ")
        assert len(model.calls) == 2

    asyncio.run(scenario())


def test_receive_after_dead_turn_is_not_blocked_by_earlier_overlap() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        await store.claim(62, _START)
        sender = RecordingSender()
        model = ScriptModel([_reply("không", "end_turn")])
        clock = Clock(_START + timedelta(seconds=10))
        deferred = await _go(store, sender, model, clock, 62, "tin treo", plans=BoomPlans())
        assert deferred is Outcome.Defer
        assert sender.parts == []
        assert (await store.claim(62, _START)).reply is None
        clock.moment = _START + timedelta(seconds=91)
        await _go(store, sender, model, clock, 62, "tin treo", plans=BoomPlans())
        assert sender.parts == [(_CHAT, _UNCERTAIN)]
        assert model.calls == []

    asyncio.run(scenario())


def test_redelivered_after_sent_fixed_sentence_sends_nothing() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        model = ScriptModel([_reply("không", "end_turn")])
        clock = Clock(_START)
        await _go(store, sender, model, clock, 63, None, plans=BoomPlans())
        assert sender.parts == [(_CHAT, _FIXED)]
        clock.moment = _START + timedelta(seconds=1)
        await _go(store, sender, model, clock, 63, None, plans=BoomPlans())
        assert sender.parts == [(_CHAT, _FIXED)]
        assert model.calls == []

    asyncio.run(scenario())


def test_non_text_and_its_fixed_sentence_never_reach_model() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        await _go(store, RecordingSender(), ScriptModel([]), clock, 64, None, plans=BoomPlans())
        clock.moment = _START + timedelta(seconds=1)
        model = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 65, "tin chữ")
        blob = " ".join(text for _role, text in _texts(model.calls[0]))
        assert _FIXED not in blob
        assert blob == "tin chữ"

    asyncio.run(scenario())


@pytest.mark.parametrize("case_id", ["crashed_update", "unexpected_exception", "d021_sentence"])
def test_uncertain_pairs_enter_context_like_normal_pairs(
    case_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        clock = Clock(_START)
        sender = RecordingSender()
        if case_id == "crashed_update":
            await store.claim(70, _START)
            clock.moment = _START + timedelta(seconds=91)
            model = ScriptModel([_reply("không", "end_turn")])
            await _go(store, sender, model, clock, 70, "tin gãy", plans=BoomPlans())
            expected = [("user", "tin gãy"), ("assistant", _UNCERTAIN)]
        elif case_id == "unexpected_exception":

            async def _boom(*_args: object, **_kwargs: object) -> str:
                raise RuntimeError("nổ")

            monkeypatch.setattr("api.telegram_update.run_turn", _boom)
            model = ScriptModel([_reply("không", "end_turn")])
            await _go(store, sender, model, clock, 71, "tin nổ", plans=BoomPlans())
            monkeypatch.undo()
            expected = [("user", "tin nổ"), ("assistant", _UNCERTAIN)]
        else:
            await store.claim(72, _START)
            assert await store.save_reply_if_absent(72, _D021) is True
            model = ScriptModel([_reply("không", "end_turn")])
            await _go(store, sender, model, clock, 72, "việc đã ghi", plans=BoomPlans())
            expected = [("user", "việc đã ghi"), ("assistant", _D021)]
        clock.moment = clock.moment + timedelta(seconds=1)
        follow = ScriptModel([_reply("tiếp", "end_turn")])
        await _go(store, RecordingSender(), follow, clock, 80, "tiếp theo")
        assert _texts(follow.calls[0]) == expected + [("user", "tiếp theo")]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("case_id", "sentence"),
    [("exact_4096", "a" * 4096), ("emoji_2049", "\U0001f600" * 2049)],
)
def test_long_reply_parts_reach_client_in_order(case_id: str, sentence: str) -> None:
    expected_parts = 1 if case_id == "exact_4096" else 2
    del case_id

    async def scenario() -> None:
        sender = RecordingSender()
        await _go(MemoryTelegramChannel(), sender, ScriptModel([_reply(sentence, "end_turn")]), Clock(_START), 90, "tin")
        parts = [text for _chat, text in sender.parts]
        assert parts == list(split_utf16(sentence))
        assert len(parts) == expected_parts
        assert "".join(parts) == sentence
        assert all(part != "" for part in parts)
        assert all(1 <= len(part.encode("utf-16-le")) // 2 <= 4096 for part in parts)

    asyncio.run(scenario())


def test_long_reply_is_one_context_message() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sentence = "a" * 4096 + "b"
        clock = Clock(_START)
        await _go(store, RecordingSender(), ScriptModel([_reply(sentence, "end_turn")]), clock, 91, "tin dài")
        rows = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assistants = [row.body for row in rows if row.role == "assistant"]
        assert assistants == [sentence]
        clock.moment = _START + timedelta(seconds=1)
        model = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), model, clock, 92, "sau")
        assistant_messages = [text for role, text in _texts(model.calls[0]) if role == "assistant"]
        assert assistant_messages == [sentence]

    asyncio.run(scenario())


def test_blank_text_uncertain_does_not_enter_context() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        await store.claim(93, _START)
        sender = RecordingSender()
        model = ScriptModel([_reply("không", "end_turn")])
        clock = Clock(_START + timedelta(seconds=91))
        done = await _go(store, sender, model, clock, 93, "   ", plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, _UNCERTAIN)]
        assert model.calls == []
        rows = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert [row for row in rows if row.update_id == 93] == []
        clock.moment = _START + timedelta(seconds=92)
        follow = ScriptModel([_reply("ok", "end_turn")])
        await _go(store, RecordingSender(), follow, clock, 94, "tin sau")
        assert all(text.strip() != "" for _role, text in _texts(follow.calls[0]))
        assert ("user", "   ") not in _texts(follow.calls[0])

    asyncio.run(scenario())


def test_context_read_failure_defers_without_model_or_send() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = FailListRecent()
        sender = RecordingSender()
        model = ScriptModel([_reply("không", "end_turn")])
        plans = BoomPlans()
        clock = Clock(_START)
        deferred = await _go(store, sender, model, clock, 95, "tin chữ", plans=plans)
        assert deferred is Outcome.Defer
        assert model.calls == []
        assert sender.parts == []
        store.fail = False
        assert await store.list_recent(_CHAT, _START - timedelta(hours=1), 20) == ()
        store.fail = True
        clock.moment = _START + timedelta(seconds=10)
        again = await _go(store, sender, model, clock, 95, "tin chữ", plans=plans)
        assert again is Outcome.Defer
        assert sender.parts == []
        assert model.calls == []
        clock.moment = _START + timedelta(seconds=91)
        later = await _go(store, sender, model, clock, 95, "tin chữ", plans=plans)
        assert later is Outcome.Done
        assert sender.parts == [(_CHAT, _UNCERTAIN)]
        assert model.calls == []

    asyncio.run(scenario())


def test_model_fixed_sentence_is_stored_as_normal_pair() -> None:
    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        sentence = "Mình chỉ đọc được tin chữ."
        model = ScriptModel([_reply(sentence, "end_turn")])
        await _go(store, sender, model, clock, 97, "tin chữ thường", plans=BoomPlans())
        rows = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert {(row.role, row.body) for row in rows} == {
            ("user", "tin chữ thường"),
            ("assistant", sentence),
        }

    asyncio.run(scenario())


def test_missing_key_redelivery_does_not_send_again() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        clock = Clock(_START)
        model = ScriptModel([_reply("không", "end_turn")])
        done = await _go(store, sender, model, clock, 98, "tin thiếu khóa", api_key=None, plans=BoomPlans())
        assert done is Outcome.Done
        assert sender.parts == [(_CHAT, "Thiếu ANTHROPIC_API_KEY.")]
        before = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        clock.moment = _START + timedelta(seconds=1)
        again = await _go(store, sender, model, clock, 98, "tin thiếu khóa", api_key=None, plans=BoomPlans())
        assert again is Outcome.Done
        assert sender.parts == [(_CHAT, "Thiếu ANTHROPIC_API_KEY.")]
        after = await store.list_recent(_CHAT, _START - timedelta(hours=1), 20)
        assert [(row.update_id, row.role, row.body) for row in after] == [
            (row.update_id, row.role, row.body) for row in before
        ]

    asyncio.run(scenario())


_CHANNEL_KEYS = {"outcome", "reason", "update_id", "error_type", "error_code"}


def _channel_line(lines: list[str]) -> dict[str, object]:
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert set(payload) <= _CHANNEL_KEYS
    assert "outcome" in payload
    assert "reason" in payload
    return payload


async def _two_plans(plans: MemoryPlanStore) -> str:
    from core.morning import render_digest
    from core.plans import Subtask, SubtaskStatus

    await plans.add("Cũ", (Subtask(id="a", title="việc cũ", status=SubtaskStatus.PENDING, note="ghi"),))
    await plans.add("Mới", (Subtask(id="b", title="việc mới", status=SubtaskStatus.PENDING, note=None),))
    return render_digest(await plans.list_newest_first())


def test_next_command_replies_with_render_digest_and_skips_the_model() -> None:
    from api.telegram_update import Outcome
    from core.morning import digest_update_id
    from core.telegram_channel import select_context

    async def scenario() -> None:
        plans = MemoryPlanStore()
        text = await _two_plans(plans)
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        model = ScriptModel([_reply("không được gọi", "end_turn")])
        lines: list[str] = []
        done = await _go(store, sender, model, Clock(_START), 41, "/next", plans=plans, log=lines)
        assert done is Outcome.Done
        assert model.calls == []
        assert sender.parts == [(_CHAT, text)]
        assert text == "Cũ\nviệc cũ\n\nMới\nviệc mới"
        payload = _channel_line(lines)
        assert payload["outcome"] == "done"
        assert payload["reason"] == "replied"
        assert payload["update_id"] == 41
        rows = select_context(
            await store.list_recent(_CHAT, _START - timedelta(hours=1), 20),
            _START,
        )
        assert [(row.role, row.body) for row in rows] == [("user", "/next"), ("assistant", text)]
        day_id = digest_update_id(date(2026, 6, 1))
        assert day_id == -20260601
        assert day_id not in store._updates

    asyncio.run(scenario())


def test_next_plan_read_error_defers_without_the_uncertain_sentence() -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        model = ScriptModel([_reply(_UNCERTAIN, "end_turn")])
        lines: list[str] = []
        deferred = await _go(store, sender, model, Clock(_START), 42, "/next", plans=BoomPlans(), log=lines)
        assert deferred is Outcome.Defer
        assert model.calls == []
        assert sender.parts == []
        payload = _channel_line(lines)
        assert payload["outcome"] == "defer"
        assert payload["reason"] == "store_unavailable"
        assert _UNCERTAIN not in lines[0]
        assert store._updates[42].reply is None
        assert store._updates[42].sent_at is None

    asyncio.run(scenario())


def test_next_redelivery_uses_decide_receive() -> None:
    from api.telegram_update import Outcome
    from core.plans import Subtask, SubtaskStatus

    async def scenario() -> None:
        plans = MemoryPlanStore()
        text = await _two_plans(plans)
        store = MemoryTelegramChannel()
        sender = RecordingSender(fail_on=1)
        model = ScriptModel([_reply("không được gọi", "end_turn")])
        first = await _go(store, sender, model, Clock(_START), 43, "/next", plans=plans)
        assert first is Outcome.Defer
        assert model.calls == []
        assert sender.parts == []
        await plans.add("Đổi", (Subtask(id="c", title="việc khác", status=SubtaskStatus.PENDING, note=None),))
        sender.fail_on = None
        clock = Clock(_START + timedelta(seconds=1))
        second = await _go(store, sender, model, clock, 43, "/next", plans=plans)
        assert second is Outcome.Done
        assert sender.parts == [(_CHAT, text)]
        assert model.calls == []
        sender.parts.clear()
        clock.moment = _START + timedelta(seconds=2)
        third = await _go(store, sender, model, clock, 43, "/next", plans=plans)
        assert third is Outcome.Done
        assert sender.parts == []
        assert model.calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize("text", ["/start", "/next hôm nay", "/next@bot"])
def test_plain_texts_still_enter_the_model_turn(text: str) -> None:
    from api.telegram_update import Outcome

    async def scenario() -> None:
        store = MemoryTelegramChannel()
        sender = RecordingSender()
        model = ScriptModel([_reply("trả lời thường", "end_turn")])
        done = await _go(store, sender, model, Clock(_START), 44, text, plans=BoomPlans())
        assert done is Outcome.Done
        assert len(model.calls) == 1
        assert _texts(model.calls[0])[-1] == ("user", text)
        assert sender.parts == [(_CHAT, "trả lời thường")]

    asyncio.run(scenario())
