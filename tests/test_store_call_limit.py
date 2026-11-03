"""Giới hạn từng lời gọi kho. Kho giả, không mở mạng."""

import asyncio
import json
import time

import httpx
import pytest

from core.plans import Plan, PlanConflictError, Subtask, SubtaskStatus
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import WriteEffect
from tools.saved_reply import REJECTED_SENTENCE, UNAVAILABLE_SENTENCE, UNCERTAIN_SENTENCE
from db.client import postgrest_client
from tools.tool_router import execute_tool

_PLAN_ID = "11111111-1111-4111-8111-111111111111"
_SUBTASK_ID = "22222222-2222-4222-8222-222222222222"
_LOG_KEYS = [
    "tool",
    "input",
    "ok",
    "error_type",
    "duration_ms",
    "definitions_version",
    "detail",
]


class _CountingStore(MemoryPlanStore):
    """Đếm lời gọi. Có thể treo hoặc ném ở đúng một phương thức."""

    def __init__(self, hang: str | None = None, error: BaseException | None = None, method: str = "add") -> None:
        super().__init__()
        self.calls: list[str] = []
        self._hang = hang
        self._error = error
        self._method = method

    async def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        self.calls.append("add")
        await self._maybe_block("add")
        return await super().add(goal, subtasks)

    async def list_newest_first(self) -> tuple[Plan, ...]:
        self.calls.append("list_newest_first")
        await self._maybe_block("list_newest_first")
        return await super().list_newest_first()

    async def get(self, plan_id: str) -> Plan | None:
        self.calls.append("get")
        await self._maybe_block("get")
        return await super().get(plan_id)

    async def replace(self, plan: Plan) -> None:
        self.calls.append("replace")
        await self._maybe_block("replace")
        await super().replace(plan)

    async def _maybe_block(self, name: str) -> None:
        if self._error is not None and name == self._method:
            raise self._error
        if self._hang == name:
            await asyncio.Event().wait()


def _seed(store: MemoryPlanStore) -> None:
    store._plans.append(
        Plan(
            id=_PLAN_ID,
            goal="Học tiếng Nhật",
            subtasks=(
                Subtask(
                    id=_SUBTASK_ID,
                    title="Học hiragana",
                    status=SubtaskStatus.PENDING,
                    note=None,
                ),
            ),
            created_order=1,
            version=0,
        )
    )
    store._next_order = 2


async def _execute(name: str, tool_input: dict, store: MemoryPlanStore, remaining=None):
    lines: list[str] = []
    kwargs = {"store": store, "log": lines.append}
    if remaining is not None:
        kwargs["remaining"] = remaining
    result = await execute_tool(name, tool_input, **kwargs)
    logged = json.loads(lines[0])
    return result, logged


def _within_two(coro):
    return asyncio.wait_for(coro, timeout=2)


def test_hung_write_returns_uncertain_sentence() -> None:
    store = _CountingStore(hang="add")

    async def _case():
        result, logged = await _execute(
            "create_plan",
            {"goal": "Học tiếng Nhật", "subtasks": ["Học hiragana"]},
            store,
            remaining=lambda: 0.05,
        )
        assert result.success is False
        assert result.output == UNCERTAIN_SENTENCE
        assert result.effect == WriteEffect(kind="uncertain")
        assert logged["ok"] is False
        assert list(logged) == _LOG_KEYS

    asyncio.run(_within_two(_case()))


def test_hung_read_does_not_write_afterwards() -> None:
    store = _CountingStore(hang="get")
    _seed(store)

    async def _case():
        result, _logged = await _execute(
            "update_subtask",
            {"plan_id": _PLAN_ID, "subtask_id": _SUBTASK_ID, "status": "done"},
            store,
            remaining=lambda: 0.05,
        )
        assert result.success is False
        assert result.output == UNAVAILABLE_SENTENCE
        assert result.output != UNCERTAIN_SENTENCE
        assert result.effect is None
        assert store.calls == ["get"]

    asyncio.run(_within_two(_case()))


def test_read_then_hung_write_returns_uncertain_sentence() -> None:
    store = _CountingStore(hang="replace")
    _seed(store)

    async def _case():
        result, _logged = await _execute(
            "add_subtask",
            {"plan_id": _PLAN_ID, "title": "Mua vở"},
            store,
            remaining=lambda: 0.05,
        )
        assert result.success is False
        assert result.output == UNCERTAIN_SENTENCE
        assert result.effect == WriteEffect(kind="uncertain")
        assert store.calls == ["get", "replace"]

    asyncio.run(_within_two(_case()))


def test_non_positive_remaining_does_not_call_store() -> None:
    store = _CountingStore()

    async def _case():
        result, _logged = await _execute(
            "create_plan",
            {"goal": "Học tiếng Nhật"},
            store,
            remaining=lambda: 0.0,
        )
        assert store.calls == []
        assert result.success is False
        assert result.output == UNAVAILABLE_SENTENCE
        assert result.effect is None

    asyncio.run(_case())


def test_httpx_connect_error_stays_unexpected() -> None:
    store = _CountingStore(error=httpx.ConnectError("connection dropped"), method="add")

    async def _case():
        result, logged = await _execute(
            "create_plan",
            {"goal": "Học tiếng Nhật"},
            store,
        )
        assert result.success is False
        assert result.output == UNAVAILABLE_SENTENCE
        assert result.effect is None
        assert logged["error_type"] == "unexpected"
        assert logged["detail"] == "ConnectError"
        assert list(logged) == _LOG_KEYS

    asyncio.run(_case())


def test_in_budget_result_matches_call_without_limit() -> None:
    plain = _CountingStore()
    limited = _CountingStore()
    _seed(plain)
    _seed(limited)
    missing = {"plan_id": "khong-co"}
    detail = {"plan_id": _PLAN_ID}
    update = {"plan_id": _PLAN_ID, "subtask_id": _SUBTASK_ID, "status": "done"}

    async def _case():
        write_plain, _plain_log = await _execute("update_subtask", update, plain)
        write_limited, _limited_log = await _execute(
            "update_subtask",
            update,
            limited,
            remaining=lambda: 20.0,
        )
        assert write_limited.success is True
        assert write_limited.output == write_plain.output
        domain_plain, domain_plain_log = await _execute("get_plan_detail", missing, plain)
        domain_limited, domain_limited_log = await _execute(
            "get_plan_detail",
            missing,
            limited,
            remaining=lambda: 20.0,
        )
        assert domain_limited.output == domain_plain.output
        assert domain_limited_log["error_type"] == "domain"
        assert domain_plain_log["error_type"] == "domain"
        read_plain_store = _CountingStore()
        _seed(read_plain_store)
        read_plain, _read_plain_log = await _execute("get_plan_detail", detail, read_plain_store)
        read_store = _CountingStore()
        _seed(read_store)
        read_limited, _read_limited_log = await _execute(
            "get_plan_detail",
            detail,
            read_store,
            remaining=lambda: 20.0,
        )
        assert read_limited.success is True
        assert read_limited.output == read_plain.output

    asyncio.run(_case())


def test_conflict_is_domain_and_does_not_retry() -> None:
    class _ConflictOnce(MemoryPlanStore):
        def __init__(self) -> None:
            super().__init__()
            self.replaces = 0

        async def replace(self, plan: Plan) -> None:
            self.replaces += 1
            raise PlanConflictError()

    store = _ConflictOnce()
    _seed(store)

    async def _case():
        result, logged = await _execute(
            "add_subtask",
            {"plan_id": _PLAN_ID, "title": "Mua vở"},
            store,
        )
        assert result.success is False
        assert result.output == REJECTED_SENTENCE
        assert result.effect == WriteEffect(kind="rejected")
        assert store.replaces == 1
        assert logged["error_type"] == "domain"
        assert list(logged) == _LOG_KEYS

    asyncio.run(_case())


def _remaining_script(values: list[float]):
    """Trả lần lượt các số. Lần gọi sau dãy ném AssertionError."""

    calls: list[int] = []
    pending = iter(values)

    def remaining() -> float:
        calls.append(1)
        try:
            return next(pending)
        except StopIteration as error:
            raise AssertionError("remaining được gọi lần thứ ba") from error

    return calls, remaining


def test_remaining_is_read_again_before_the_write() -> None:
    store = _CountingStore()
    _seed(store)
    calls, remaining = _remaining_script([20.0, 0.0])

    async def _case():
        result, _logged = await _execute(
            "add_subtask",
            {"plan_id": _PLAN_ID, "title": "Mua vở"},
            store,
            remaining=remaining,
        )
        assert store.calls == ["get"]
        assert result.success is False
        assert result.output == UNAVAILABLE_SENTENCE
        assert result.effect is None
        assert len(calls) == 2

    asyncio.run(_case())


def test_second_store_call_uses_a_fresh_remaining_value() -> None:
    store = _CountingStore(hang="replace")
    _seed(store)
    calls, remaining = _remaining_script([20.0, 0.05])

    async def _case():
        started = time.monotonic()
        result, _logged = await _execute(
            "add_subtask",
            {"plan_id": _PLAN_ID, "title": "Mua vở"},
            store,
            remaining=remaining,
        )
        elapsed = time.monotonic() - started
        assert result.output == UNCERTAIN_SENTENCE
        assert result.effect == WriteEffect(kind="uncertain")
        assert store.calls == ["get", "replace"]
        assert len(calls) == 2
        assert elapsed < 1.0

    asyncio.run(_case())


def test_cancel_during_hung_add_propagates() -> None:
    store = _CountingStore(hang="add")

    async def _case():
        task = asyncio.create_task(
            execute_tool("create_plan", {"goal": "Học tiếng Nhật"}, store=store)
        )

        async def _started() -> None:
            while store.calls != ["add"]:
                await asyncio.sleep(0)

        await asyncio.wait_for(_started(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_case())


def test_postgrest_session_uses_twenty_second_ceiling() -> None:
    async def _check(key: str) -> None:
        async with postgrest_client("http://x.invalid", key) as client:
            timeout = client.session.timeout
            assert timeout.connect == 20
            assert timeout.read == 20
            assert timeout.write == 20
            assert timeout.pool == 20
            assert client.session.follow_redirects is True
            assert "/rest/v1" in str(client.base_url)
            assert client.headers["apikey"] == key
            if key.startswith("eyJ"):
                assert client.headers["Authorization"] == f"Bearer {key}"
            else:
                assert "Authorization" not in client.headers

    asyncio.run(_check("key"))
    asyncio.run(_check("eyJ-test"))
