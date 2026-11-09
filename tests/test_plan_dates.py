"""Hạn, trùng hạn, việc dời ngày, và mã ngày, ưu tiên, sức."""

from datetime import date

import pytest

from core.plans import (
    EFFORT_HOURS,
    Effort,
    Plan,
    PlanDomainError,
    Priority,
    Subtask,
    SubtaskStatus,
    date_moves,
    deadline_clash,
    normalize_priority,
    normalize_scheduled_on,
    plan_deadline,
)


def _item(
    title: str,
    *,
    status: SubtaskStatus = SubtaskStatus.PENDING,
    scheduled_on: date | None = None,
) -> Subtask:
    return Subtask(id=title, title=title, status=status, note=None, scheduled_on=scheduled_on)


def _plan(*items: Subtask, plan_id: str = "plan") -> Plan:
    return Plan(id=plan_id, goal="Mục tiêu", subtasks=items, created_order=1, version=0)


def test_plan_deadline_is_latest_pending_date() -> None:
    plan = _plan(
        _item("Sớm", scheduled_on=date(2026, 11, 6)),
        _item("Muộn", scheduled_on=date(2026, 11, 8)),
    )
    assert plan_deadline(plan) == date(2026, 11, 8)


def test_plan_deadline_ignores_done_skipped_and_undated() -> None:
    plan = _plan(
        _item("Xong", status=SubtaskStatus.DONE, scheduled_on=date(2026, 11, 9)),
        _item("Bỏ", status=SubtaskStatus.SKIPPED, scheduled_on=date(2026, 11, 10)),
        _item("Chưa ngày"),
        _item("Còn", scheduled_on=date(2026, 11, 6)),
    )
    assert plan_deadline(plan) == date(2026, 11, 6)


def test_plan_deadline_is_none_when_no_pending_date() -> None:
    plan = _plan(
        _item("Xong", status=SubtaskStatus.DONE, scheduled_on=date(2026, 11, 6)),
        _item("Chưa ngày"),
    )
    assert plan_deadline(plan) is None


def test_deadline_clash_skips_the_same_plan_id() -> None:
    day = date(2026, 11, 6)
    after = _plan(_item("Việc", scheduled_on=day), plan_id="cùng")
    other = _plan(_item("Khác", scheduled_on=day), plan_id="khác")
    found = deadline_clash(after, (after, other))
    assert found is not None
    assert found.id == "khác"


def test_date_moves_includes_date_to_other_date() -> None:
    before = _plan(_item("Việc", scheduled_on=date(2026, 11, 6)))
    after = _plan(_item("Việc", scheduled_on=date(2026, 11, 7)))
    moved = date_moves(before, after)
    assert [item.id for item in moved] == ["Việc"]
    assert moved[0].scheduled_on == date(2026, 11, 7)


def test_date_moves_excludes_empty_to_date() -> None:
    before = _plan(_item("Việc"))
    after = _plan(_item("Việc", scheduled_on=date(2026, 11, 6)))
    assert date_moves(before, after) == ()


def test_date_moves_excludes_date_to_empty() -> None:
    before = _plan(_item("Việc", scheduled_on=date(2026, 11, 6)))
    after = _plan(_item("Việc"))
    assert date_moves(before, after) == ()


def test_date_moves_excludes_same_date() -> None:
    before = _plan(_item("Việc", scheduled_on=date(2026, 11, 6)))
    after = _plan(_item("Việc", scheduled_on=date(2026, 11, 6)))
    assert date_moves(before, after) == ()


def test_bad_iso_date_is_domain_error() -> None:
    with pytest.raises(PlanDomainError):
        normalize_scheduled_on("06/11/2026")


def test_bad_priority_is_domain_error() -> None:
    with pytest.raises(PlanDomainError):
        normalize_priority("urgent")


def test_effort_hours_are_one_three_six() -> None:
    assert EFFORT_HOURS == {Effort.S: 1, Effort.M: 3, Effort.L: 6}
    assert Priority.HIGH.value == "high"
