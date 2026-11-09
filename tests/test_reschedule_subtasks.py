"""Dời ngày: chưa có ngữ cảnh thì không ghi, trùng hạn thì hỏi, lịch sử chỉ ngày sang ngày."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from core.plans import PlanDomainError
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, TurnContext
from tools.plan_tools import create_plan, reschedule_subtasks, update_subtask
from tools.saved_reply import compose

_INSTANT = datetime(2026, 11, 6, 8, 0, tzinfo=timezone(timedelta(hours=2)))


class _CountingStore(MemoryPlanStore):
    """Đếm replace. Đọc không tính là ghi."""

    def __init__(self) -> None:
        super().__init__()
        self.writes = 0

    async def replace(self, plan, *, move_reason=None, moved_at=None) -> None:  # type: ignore[override]
        self.writes += 1
        await super().replace(plan, move_reason=move_reason, moved_at=moved_at)


def _turn() -> TurnContext:
    return TurnContext(instant=_INSTANT)


def _make(store: MemoryPlanStore, goal: str, items: list[dict[str, str]]) -> dict:
    result = asyncio.run(create_plan(goal, items, store=store))
    assert result.success is True
    return json.loads(result.output)


def test_reschedule_without_turn_context_does_not_write() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    before = store.writes
    with pytest.raises(ToolError):
        asyncio.run(
            reschedule_subtasks(
                plan["id"],
                [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-07"}],
                store=store,
            )
        )
    assert store.writes == before
    assert store.date_moves == []


def test_clash_without_confirm_does_not_write() -> None:
    store = _CountingStore()
    other = _make(store, "Nộp báo cáo", [{"title": "Nộp", "scheduled_on": "2026-11-20"}])
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    before = store.writes
    turn = _turn()
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-20"}],
            store=store,
            turn=turn,
        )
    )
    assert result.success is True
    assert result.effect is None
    assert compose(()) == ""
    assert "chưa ghi" in result.output
    assert "Nộp báo cáo" in result.output
    assert "2026-11-20" in result.output
    assert plan["id"] not in result.output
    assert other["id"] not in result.output
    assert plan["subtasks"][0]["id"] not in result.output
    assert other["subtasks"][0]["id"] not in result.output
    assert turn.clash_reported is True
    assert store.writes == before
    assert store.date_moves == []


def test_confirm_after_flag_in_same_context_is_tool_error() -> None:
    store = _CountingStore()
    _make(store, "Nộp báo cáo", [{"title": "Nộp", "scheduled_on": "2026-11-20"}])
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    turn = _turn()
    asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-20"}],
            store=store,
            turn=turn,
        )
    )
    before = store.writes
    with pytest.raises(ToolError):
        asyncio.run(
            reschedule_subtasks(
                plan["id"],
                [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-20"}],
                confirm=True,
                store=store,
                turn=turn,
            )
        )
    assert store.writes == before
    assert store.date_moves == []


def test_confirm_on_a_new_context_writes() -> None:
    store = _CountingStore()
    _make(store, "Nộp báo cáo", [{"title": "Nộp", "scheduled_on": "2026-11-20"}])
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-20"}],
            confirm=True,
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert result.effect is not None
    assert store.writes == 1
    assert len(store.date_moves) == 1
    assert store.date_moves[0].moved_at == _INSTANT


def test_no_clash_writes_without_confirm() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-07"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    assert len(store.date_moves) == 1
    assert store.date_moves[0].to_date.isoformat() == "2026-11-07"


def test_unchanged_deadline_does_not_ask() -> None:
    store = _CountingStore()
    _make(store, "Nộp báo cáo", [{"title": "Nộp", "scheduled_on": "2026-11-20"}])
    plan = _make(
        store,
        "Học",
        [
            {"title": "Hiragana", "scheduled_on": "2026-11-06"},
            {"title": "Katakana", "scheduled_on": "2026-11-20"},
        ],
    )
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-08"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    assert len(store.date_moves) == 1


def test_moved_plan_is_not_compared_with_itself() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-09"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    assert len(store.date_moves) == 1


def test_deadline_ignores_done_and_undated() -> None:
    store = _CountingStore()
    other = _make(
        store,
        "Nộp báo cáo",
        [
            {"title": "Nộp", "scheduled_on": "2026-11-20"},
            {"title": "Đã xong", "scheduled_on": "2026-11-10"},
            {"title": "Chưa ngày"},
        ],
    )
    asyncio.run(
        update_subtask(other["id"], other["subtasks"][1]["id"], "done", store=store)
    )
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-10"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    assert len(store.date_moves) == 1


def test_reschedule_with_no_change_does_not_write() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    result = asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-06"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert result.effect is None
    assert store.writes == 0
    assert store.date_moves == []


def test_reschedule_empty_changes_is_domain_error() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    with pytest.raises(PlanDomainError):
        asyncio.run(reschedule_subtasks(plan["id"], [], store=store, turn=_turn()))
    assert store.writes == 0


def test_reschedule_duplicate_subtask_id_is_domain_error() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    subtask_id = plan["subtasks"][0]["id"]
    with pytest.raises(PlanDomainError):
        asyncio.run(
            reschedule_subtasks(
                plan["id"],
                [
                    {"subtask_id": subtask_id, "scheduled_on": "2026-11-07"},
                    {"subtask_id": subtask_id, "scheduled_on": "2026-11-08"},
                ],
                store=store,
                turn=_turn(),
            )
        )
    assert store.writes == 0
    assert store.date_moves == []


def test_reschedule_unknown_subtask_id_is_domain_error() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    with pytest.raises(PlanDomainError):
        asyncio.run(
            reschedule_subtasks(
                plan["id"],
                [{"subtask_id": "không-có", "scheduled_on": "2026-11-07"}],
                store=store,
                turn=_turn(),
            )
        )
    assert store.writes == 0
    assert store.date_moves == []


def test_reschedule_blank_reason_is_stored_as_none() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-07"}],
            reason="   ",
            store=store,
            turn=_turn(),
        )
    )
    assert len(store.date_moves) == 1
    assert store.date_moves[0].reason is None


def test_reschedule_reason_is_trimmed() -> None:
    store = _CountingStore()
    plan = _make(store, "Học", [{"title": "Hiragana", "scheduled_on": "2026-11-06"}])
    asyncio.run(
        reschedule_subtasks(
            plan["id"],
            [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-07"}],
            reason="  hết việc  ",
            store=store,
            turn=_turn(),
        )
    )
    assert len(store.date_moves) == 1
    assert store.date_moves[0].reason == "hết việc"
