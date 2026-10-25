"""Ánh xạ dòng đọc từ kho sang Plan. Không tạo store và không mở mạng."""

import pytest

from core.plans import Plan, PlanDomainError, SubtaskStatus
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
    assert set(plan.subtasks[0].__dataclass_fields__) == {"id", "title", "status", "note"}


def test_missing_subtasks_is_mapping_error() -> None:
    row = _row()
    del row["subtasks"]
    with pytest.raises(ValueError, match="Thiếu khóa subtasks"):
        plan_from_row(row)


def test_empty_subtasks() -> None:
    plan = plan_from_row(_row(subtasks=[]))
    assert plan.subtasks == ()


def test_strange_status_rejects_the_plan() -> None:
    row = _row(
        subtasks=[_subtask(0, "later", None, "Lạ", _FIRST_ID)],
    )
    with pytest.raises(PlanDomainError) as caught:
        plan_from_row(row)
    assert str(caught.value) == "Trạng thái việc con đã lưu không hợp lệ."
