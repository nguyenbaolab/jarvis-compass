"""Ánh xạ dòng đọc từ kho sang Plan. Không tạo store và không mở mạng."""

import pytest

from datetime import date

from core.plans import Effort, Plan, PlanDomainError, Priority, SubtaskStatus
from db.plan_store import plan_from_row

_PLAN_ID = "11111111-1111-4111-8111-111111111111"
_FIRST_ID = "22222222-2222-4222-8222-222222222222"
_SECOND_ID = "33333333-3333-4333-8333-333333333333"


def _subtask(position: int, status: str, note: str | None, title: str, subtask_id: str) -> dict:
    return {
        "id": subtask_id,
        "title": title,
        "status": status,
        "note": note,
        "position": position,
        "created_at": "2026-10-25T00:00:00+00:00",
        "status_changed_at": "2026-10-25T00:00:01+00:00",
    }


def _row(subtasks: list[dict] | None = None) -> dict:
    if subtasks is None:
        subtasks = [
            _subtask(1, "pending", None, "Học hiragana", _SECOND_ID),
            _subtask(0, "done", "", "Đầu", _FIRST_ID),
        ]
    return {
        "id": _PLAN_ID,
        "goal": "Học tiếng Nhật",
        "created_order": 2,
        "version": 0,
        "subtasks": subtasks,
    }


def test_valid_row_becomes_plan() -> None:
    plan = plan_from_row(_row())
    assert isinstance(plan, Plan)
    assert plan.id == _PLAN_ID
    assert plan.goal == "Học tiếng Nhật"
    assert plan.created_order == 2
    assert [item.id for item in plan.subtasks] == [_FIRST_ID, _SECOND_ID]
    assert plan.subtasks[0].title == "Đầu"
    assert plan.subtasks[0].status is SubtaskStatus.DONE
    assert plan.subtasks[0].note is None
    assert plan.subtasks[1].note is None
    assert set(plan.subtasks[0].__dataclass_fields__) == {
        "id",
        "title",
        "status",
        "note",
        "scheduled_on",
        "effort",
    }


def test_missing_subtasks_is_mapping_error() -> None:
    row = _row()
    del row["subtasks"]
    with pytest.raises(ValueError, match="Thiếu khóa subtasks"):
        plan_from_row(row)


def test_empty_subtasks() -> None:
    plan = plan_from_row(_row(subtasks=[]))
    assert plan.subtasks == ()


def test_row_without_version_is_mapping_error() -> None:
    row = _row()
    del row["version"]
    with pytest.raises(KeyError, match="version"):
        plan_from_row(row)


def test_row_version_seven_becomes_plan_version() -> None:
    row = _row()
    row["version"] = 7
    assert plan_from_row(row).version == 7


def test_strange_status_rejects_the_plan() -> None:
    row = _row(
        subtasks=[_subtask(0, "later", None, "Lạ", _FIRST_ID)],
    )
    with pytest.raises(PlanDomainError) as caught:
        plan_from_row(row)
    assert str(caught.value) == "Trạng thái việc con đã lưu không hợp lệ."


def test_row_without_new_columns_is_empty() -> None:
    plan = plan_from_row(_row())
    assert plan.priority is None
    assert plan.subtasks[0].scheduled_on is None
    assert plan.subtasks[0].effort is None
    assert plan.subtasks[1].scheduled_on is None
    assert plan.subtasks[1].effort is None


def test_row_maps_priority_date_and_effort() -> None:
    row = _row()
    row["priority"] = "high"
    row["subtasks"][0]["scheduled_on"] = "2026-11-08"
    row["subtasks"][0]["effort"] = "L"
    row["subtasks"][1]["scheduled_on"] = "2026-11-06"
    row["subtasks"][1]["effort"] = "S"
    plan = plan_from_row(row)
    assert plan.priority is Priority.HIGH
    dated = {item.id: item for item in plan.subtasks}
    assert dated[_SECOND_ID].scheduled_on == date(2026, 11, 8)
    assert dated[_SECOND_ID].effort is Effort.L
    assert dated[_FIRST_ID].scheduled_on == date(2026, 11, 6)
    assert dated[_FIRST_ID].effort is Effort.S
