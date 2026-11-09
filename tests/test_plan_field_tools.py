"""Ưu tiên, sức, và việc các tool khác không đụng các trường đó."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import TurnContext
from tools.plan_tools import (
    add_subtask,
    create_plan,
    reschedule_subtasks,
    set_plan_priority,
    set_subtask_effort,
    set_subtask_note,
    update_subtask,
)

_TURN = TurnContext(instant=datetime(2026, 11, 6, 8, 0, tzinfo=timezone(timedelta(hours=2))))


def _created() -> tuple[MemoryPlanStore, dict]:
    store = MemoryPlanStore()
    result = asyncio.run(
        create_plan(
            "Học tiếng Nhật",
            [{"title": "Học hiragana", "scheduled_on": "2026-11-06", "effort": "M"}],
            priority="high",
            store=store,
        )
    )
    return store, json.loads(result.output)


def test_set_plan_priority_sets() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(set_plan_priority(plan["id"], "low", store=store)).output
    )
    assert data["priority"] == "low"


def test_set_plan_priority_null_clears() -> None:
    store, plan = _created()
    data = json.loads(asyncio.run(set_plan_priority(plan["id"], None, store=store)).output)
    assert data["priority"] is None


def test_set_plan_priority_leaves_date_and_effort() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(set_plan_priority(plan["id"], "medium", store=store)).output
    )
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"
    assert data["subtasks"][0]["effort"] == "M"


def test_set_subtask_effort_sets() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            set_subtask_effort(plan["id"], plan["subtasks"][0]["id"], "L", store=store)
        ).output
    )
    assert data["subtasks"][0]["effort"] == "L"


def test_set_subtask_effort_null_clears() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            set_subtask_effort(plan["id"], plan["subtasks"][0]["id"], None, store=store)
        ).output
    )
    assert data["subtasks"][0]["effort"] is None


def test_set_subtask_effort_leaves_priority_and_date() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            set_subtask_effort(plan["id"], plan["subtasks"][0]["id"], "S", store=store)
        ).output
    )
    assert data["priority"] == "high"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"


def test_update_subtask_keeps_priority_date_and_effort() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            update_subtask(plan["id"], plan["subtasks"][0]["id"], "done", store=store)
        ).output
    )
    assert data["priority"] == "high"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"
    assert data["subtasks"][0]["effort"] == "M"
    assert data["subtasks"][0]["status"] == "done"


def test_add_subtask_keeps_priority_date_and_effort() -> None:
    store, plan = _created()
    data = json.loads(asyncio.run(add_subtask(plan["id"], "Mua vở", store=store)).output)
    assert data["priority"] == "high"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"
    assert data["subtasks"][0]["effort"] == "M"
    assert data["subtasks"][1]["title"] == "Mua vở"


def test_set_subtask_note_keeps_priority_date_and_effort() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            set_subtask_note(plan["id"], plan["subtasks"][0]["id"], "Đợi sách", store=store)
        ).output
    )
    assert data["priority"] == "high"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"
    assert data["subtasks"][0]["effort"] == "M"
    assert data["subtasks"][0]["note"] == "Đợi sách"


def test_reschedule_keeps_priority() -> None:
    store, plan = _created()
    data = json.loads(
        asyncio.run(
            reschedule_subtasks(
                plan["id"],
                [{"subtask_id": plan["subtasks"][0]["id"], "scheduled_on": "2026-11-08"}],
                store=store,
                turn=_TURN,
            )
        ).output
    )
    assert data["priority"] == "high"
    assert data["subtasks"][0]["effort"] == "M"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-08"
