"""Ba tool quét tải trên MemoryPlanStore. Không Supabase."""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from core.plans import Effort, Priority, Subtask, SubtaskStatus
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, TurnContext
from tools.plan_tools import (
    _CONFIRM_SAME_TURN,
    add_subtask,
    create_plan,
    reschedule_subtasks,
)

_ZONE = timezone(timedelta(hours=2))
_NOV12 = date(2026, 11, 12)
_SAMPLE = (
    "Lần này chưa ghi. Ngày 12/11 sẽ có 11 giờ trên quỹ 8 giờ "
    "(tính tạm: 2 việc chưa có sức, mỗi việc tính 3 giờ). "
    "Nếu vẫn ghi thì dời: 1. Học module 3 (kế hoạch Azure) sang 13/11. "
    "2. Luyện nói (kế hoạch Phần Lan) sang 14/11."
)


def _turn(day: date = date(2026, 11, 10)) -> TurnContext:
    return TurnContext(instant=datetime(day.year, day.month, day.day, 8, 0, tzinfo=_ZONE))


def _task(
    title: str,
    day: date | None,
    effort: Effort | None = None,
    *,
    status: SubtaskStatus = SubtaskStatus.PENDING,
) -> Subtask:
    return Subtask(id=title, title=title, status=status, note=None, scheduled_on=day, effort=effort)


def _ids(store: MemoryPlanStore) -> set[tuple[str, str, str | None]]:
    found: set[tuple[str, str, str | None]] = set()
    for plan in store._plans:
        for item in plan.subtasks:
            day = None if item.scheduled_on is None else item.scheduled_on.isoformat()
            found.add((plan.id, item.id, day))
    return found


def test_overload_first_call_does_not_write() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(store.add("Có", (_task("Sẵn", _NOV12, Effort.L),), priority=Priority.LOW))
    before = _ids(store)
    result = asyncio.run(
        add_subtask(
            plan.id,
            "Thêm",
            scheduled_on="2026-11-12",
            effort="L",
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "Lần này chưa ghi." in result.output
    assert _ids(store) == before


def test_overload_sentence_matches_contract() -> None:
    store = MemoryPlanStore()
    azure = asyncio.run(
        store.add("Azure", (_task("Học module 3", _NOV12, Effort.S),), priority=Priority.LOW)
    )
    asyncio.run(
        store.add(
            "Phần Lan",
            (_task("Luyện nói", _NOV12, Effort.M),),
            priority=Priority.MEDIUM,
        )
    )
    asyncio.run(
        store.add(
            "Cao",
            (_task("Chưa sức một", _NOV12), _task("Chưa sức hai", _NOV12)),
            priority=Priority.HIGH,
        )
    )
    asyncio.run(store.add("Đệm", (_task("Đầy", date(2026, 11, 13), Effort.L),)))
    result = asyncio.run(
        add_subtask(
            azure.id,
            "Việc mới",
            scheduled_on="2026-11-12",
            effort="S",
            store=store,
            turn=_turn(),
        )
    )
    assert result.output == _SAMPLE
    early = MemoryPlanStore()
    ready = asyncio.run(early.add("Sẵn", (_task("Sẵn", date(2026, 11, 6), Effort.L),)))
    early_result = asyncio.run(
        add_subtask(
            ready.id,
            "Thêm",
            scheduled_on="2026-11-06",
            effort="L",
            store=early,
            turn=_turn(date(2026, 11, 1)),
        )
    )
    assert "Ngày 06/11 sẽ có" in early_result.output
    assert "Ngày 6/11 sẽ có" not in early_result.output


def test_same_turn_confirm_does_not_write() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(store.add("Có", (_task("Sẵn", _NOV12, Effort.L),)))
    turn = _turn()
    asyncio.run(
        add_subtask(plan.id, "Thêm", scheduled_on="2026-11-12", effort="L", store=store, turn=turn)
    )
    before = _ids(store)
    with pytest.raises(ToolError) as caught:
        asyncio.run(
            add_subtask(
                plan.id,
                "Thêm",
                scheduled_on="2026-11-12",
                effort="L",
                confirm=True,
                store=store,
                turn=turn,
            )
        )
    assert str(caught.value) == _CONFIRM_SAME_TURN
    assert _ids(store) == before


def test_past_only_write_is_saved() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(store.add("Cũ", ()))
    result = asyncio.run(
        add_subtask(
            plan.id,
            "Việc",
            scheduled_on="2026-11-06",
            effort="L",
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    saved = json.loads(result.output)
    assert saved["subtasks"][-1]["scheduled_on"] == "2026-11-06"


def test_empty_move_list_invents_no_task() -> None:
    store = MemoryPlanStore()
    result = asyncio.run(
        create_plan(
            "Mới",
            [
                {"title": "Một", "scheduled_on": "2026-11-12"},
                {"title": "Hai", "scheduled_on": "2026-11-12"},
                {"title": "Ba", "scheduled_on": "2026-11-12"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    assert "tính tạm: 3 việc chưa có sức" in result.output
    assert "Nếu vẫn ghi thì dời" not in result.output
    assert store._plans == []


def test_many_days_open_once() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Có", (_task("Ngày 12", _NOV12, Effort.L), _task("Ngày 13", date(2026, 11, 13), Effort.L))))
    result = asyncio.run(
        create_plan(
            "Mới",
            [
                {"title": "Thêm 12", "scheduled_on": "2026-11-12", "effort": "L"},
                {"title": "Thêm 13", "scheduled_on": "2026-11-13", "effort": "L"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    assert result.output.count("Lần này chưa ghi.") == 1
    assert "Ngày 12/11 sẽ có" in result.output
    assert "Ngày 13/11 sẽ có" in result.output
    assert len(store._plans) == 1


def test_many_days_do_not_share_one_destination() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Có", (_task("Ngày 12", _NOV12, Effort.L), _task("Ngày 13", date(2026, 11, 13), Effort.L))))
    result = asyncio.run(
        create_plan(
            "Mới",
            [
                {"title": "Thêm 12", "scheduled_on": "2026-11-12", "effort": "L"},
                {"title": "Thêm 13", "scheduled_on": "2026-11-13", "effort": "L"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    assert "Ngày 12/11 sẽ có 12 giờ" in result.output
    assert "Ngày 13/11 sẽ có 12 giờ" in result.output
    assert "1. Ngày 12 (kế hoạch Có) sang 14/11." in result.output
    assert "2. Ngày 13 (kế hoạch Có) sang 15/11." in result.output


def test_confirmed_write_runs_request_then_moves_in_list_order() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(
        store.add(
            "Một",
            (
                _task("A", _NOV12, Effort.L),
                _task("B", _NOV12, Effort.L),
                _task("C", _NOV12, Effort.S),
            ),
        )
    )
    result = asyncio.run(
        reschedule_subtasks(
            plan.id,
            [{"subtask_id": "C", "scheduled_on": "2026-11-20"}],
            confirm=True,
            load_moves=[
                {"plan_id": plan.id, "subtask_id": "B", "scheduled_on": "2026-11-15"},
                {"plan_id": plan.id, "subtask_id": "A", "scheduled_on": "2026-11-14"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    assert result.success is True
    assert "chưa ghi" not in result.output
    assert [row.subtask_id for row in store.date_moves] == ["C", "B", "A"]
    saved = {item.id: item.scheduled_on for item in store._plans[0].subtasks}
    assert saved == {"A": date(2026, 11, 14), "B": date(2026, 11, 15), "C": date(2026, 11, 20)}


class _FailSecondReplace(MemoryPlanStore):
    """Ném lỗi ở lần replace thứ hai. Không sửa tests/fakes."""

    def __init__(self) -> None:
        super().__init__()
        self.replaces = 0

    async def replace(self, plan, *, move_reason=None, moved_at=None) -> None:  # type: ignore[override]
        self.replaces += 1
        if self.replaces == 2:
            raise RuntimeError("đứt")
        await super().replace(plan, move_reason=move_reason, moved_at=moved_at)


def test_moves_stop_at_first_error_and_report_done_and_not_done() -> None:
    store = _FailSecondReplace()
    plan = asyncio.run(store.add("Một", (_task("A", _NOV12, Effort.L), _task("B", _NOV12, Effort.L))))
    with pytest.raises(ToolError) as caught:
        asyncio.run(
            reschedule_subtasks(
                plan.id,
                [{"subtask_id": "A", "scheduled_on": "2026-11-20"}],
                confirm=True,
                load_moves=[
                    {"plan_id": plan.id, "subtask_id": "B", "scheduled_on": "2026-11-15"},
                ],
                store=store,
                turn=_turn(),
            )
        )
    assert str(caught.value) == "Đã ghi lần đang xin. Đã dời: . Chưa dời: B."
    saved = {item.id: item.scheduled_on for item in store._plans[0].subtasks}
    assert saved["A"] == date(2026, 11, 20)
    assert saved["B"] == _NOV12


def test_confirmed_write_does_not_warn_the_same_day_again() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(store.add("Có", (_task("Sẵn", _NOV12, Effort.L),)))
    result = asyncio.run(
        add_subtask(
            plan.id,
            "Thêm",
            scheduled_on="2026-11-12",
            effort="L",
            confirm=True,
            store=store,
            turn=_turn(),
        )
    )
    assert "chưa ghi" not in result.output
    assert json.loads(result.output)["subtasks"][-1]["title"] == "Thêm"


def test_reschedule_to_the_same_date_on_a_full_day_does_not_warn() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(
        store.add("Đầy", (_task("Giữ", _NOV12, Effort.L), _task("Dời", _NOV12, Effort.L)))
    )
    result = asyncio.run(
        reschedule_subtasks(
            plan.id,
            [
                {"subtask_id": "Dời", "scheduled_on": "2026-11-20"},
                {"subtask_id": "Giữ", "scheduled_on": "2026-11-12"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    assert "chưa ghi" not in result.output
    saved = {item.id: item.scheduled_on for item in store._plans[0].subtasks}
    assert saved["Dời"] == date(2026, 11, 20)
    assert saved["Giữ"] == _NOV12


def test_reschedule_over_and_clash_reports_load_then_clash_in_one_result() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Nộp", (_task("Nộp", date(2026, 11, 20), Effort.L),)))
    plan = asyncio.run(store.add("Học", (_task("Hiragana", _NOV12, Effort.L),)))
    result = asyncio.run(
        reschedule_subtasks(
            plan.id,
            [{"subtask_id": "Hiragana", "scheduled_on": "2026-11-20"}],
            store=store,
            turn=_turn(),
        )
    )
    assert result.output.count("Lần này chưa ghi.") == 1
    assert result.output.index("Lần này chưa ghi.") < result.output.index("Kế hoạch Nộp cũng đến hạn 2026-11-20.")
    assert store.date_moves == []


def test_load_moves_skip_clash_check() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Nộp", (_task("Nộp", date(2026, 11, 20), Effort.S),)))
    plan = asyncio.run(store.add("Học", (_task("Giữ", _NOV12, Effort.S), _task("Dời", date(2026, 11, 18), Effort.S))))
    asyncio.run(
        reschedule_subtasks(
            plan.id,
            [{"subtask_id": "Giữ", "scheduled_on": "2026-11-13"}],
            confirm=True,
            load_moves=[
                {"plan_id": plan.id, "subtask_id": "Dời", "scheduled_on": "2026-11-20"},
            ],
            store=store,
            turn=_turn(),
        )
    )
    saved = {item.id: item.scheduled_on for item in store._plans[1].subtasks}
    assert saved["Dời"] == date(2026, 11, 20)


def test_create_and_add_skip_clash_check() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Nộp", (_task("Nộp", date(2026, 11, 20), Effort.L),)))
    created = asyncio.run(
        create_plan(
            "Mới",
            [{"title": "Việc", "scheduled_on": "2026-11-20", "effort": "S"}],
            store=store,
            turn=_turn(),
        )
    )
    assert created.success is True
    assert "chưa ghi" not in created.output
    other = asyncio.run(store.add("Khác", ()))
    added = asyncio.run(
        add_subtask(
            other.id,
            "Thêm",
            scheduled_on="2026-11-20",
            effort="S",
            store=store,
            turn=_turn(),
        )
    )
    assert added.success is True
    assert "chưa ghi" not in added.output


def test_write_on_today_runs_the_check() -> None:
    store = MemoryPlanStore()
    today = date(2026, 11, 12)
    plan = asyncio.run(store.add("Có", (_task("Sẵn", today, Effort.L),)))
    before = _ids(store)
    result = asyncio.run(
        add_subtask(
            plan.id,
            "Thêm",
            scheduled_on="2026-11-12",
            effort="L",
            store=store,
            turn=_turn(today),
        )
    )
    assert "Lần này chưa ghi." in result.output
    assert _ids(store) == before


def test_load_move_on_missing_or_done_task_writes_nothing() -> None:
    store = MemoryPlanStore()
    plan = asyncio.run(store.add("Có", (_task("Sẵn", _NOV12, Effort.S), _task("Xong", _NOV12, Effort.S))))
    before = _ids(store)
    with pytest.raises(ToolError):
        asyncio.run(
            reschedule_subtasks(
                plan.id,
                [{"subtask_id": "Sẵn", "scheduled_on": "2026-11-13"}],
                confirm=True,
                load_moves=[
                    {"plan_id": plan.id, "subtask_id": "không-có", "scheduled_on": "2026-11-14"},
                ],
                store=store,
                turn=_turn(),
            )
        )
    assert _ids(store) == before
    done = _task("Xong", _NOV12, Effort.S, status=SubtaskStatus.DONE)
    ready = _task("Sẵn", _NOV12, Effort.S)
    second = MemoryPlanStore()
    kept = asyncio.run(second.add("Có", (ready, done)))
    before_done = _ids(second)
    with pytest.raises(ToolError):
        asyncio.run(
            reschedule_subtasks(
                kept.id,
                [{"subtask_id": "Sẵn", "scheduled_on": "2026-11-13"}],
                confirm=True,
                load_moves=[
                    {"plan_id": kept.id, "subtask_id": "Xong", "scheduled_on": "2026-11-14"},
                ],
                store=second,
                turn=_turn(),
            )
        )
    assert _ids(second) == before_done


def test_owner_removing_a_task_from_the_list_keeps_its_date() -> None:
    store = MemoryPlanStore()
    azure = asyncio.run(store.add("Azure", (_task("Học module 3", _NOV12, Effort.S),), priority=Priority.LOW))
    finland = asyncio.run(
        store.add("Phần Lan", (_task("Luyện nói", _NOV12, Effort.M),), priority=Priority.MEDIUM)
    )
    asyncio.run(store.add("Cao", (_task("Chưa sức một", _NOV12), _task("Chưa sức hai", _NOV12)), priority=Priority.HIGH))
    asyncio.run(store.add("Đệm", (_task("Đầy", date(2026, 11, 13), Effort.L),)))
    turn = _turn()
    asyncio.run(
        add_subtask(
            azure.id,
            "Việc mới",
            scheduled_on="2026-11-12",
            effort="S",
            store=store,
            turn=turn,
        )
    )
    later = _turn()
    asyncio.run(
        add_subtask(
            azure.id,
            "Việc mới",
            scheduled_on="2026-11-12",
            effort="S",
            confirm=True,
            load_moves=[
                {
                    "plan_id": finland.id,
                    "subtask_id": "Luyện nói",
                    "scheduled_on": "2026-11-16",
                },
            ],
            store=store,
            turn=later,
        )
    )
    azure = next(plan for plan in store._plans if plan.goal == "Azure")
    assert next(item for item in azure.subtasks if item.id == "Học module 3").scheduled_on == _NOV12
    assert [row.subtask_id for row in store.date_moves if row.subtask_id == "Học module 3"] == []
    finland_saved = next(plan for plan in store._plans if plan.id == finland.id)
    assert finland_saved.subtasks[0].scheduled_on == date(2026, 11, 16)
