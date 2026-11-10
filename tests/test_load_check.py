"""Tải một ngày, quỹ 8 giờ, và danh sách việc đề xuất dời. Không gọi kho."""

from datetime import date

from core.plans import (
    DayLoad,
    Effort,
    Plan,
    Priority,
    Subtask,
    SubtaskStatus,
    day_budget,
    day_load,
    propose_load_moves,
    task_hours,
)

_TODAY = date(2026, 11, 10)
_DAY = date(2026, 11, 12)


def _item(
    title: str,
    *,
    status: SubtaskStatus = SubtaskStatus.PENDING,
    scheduled_on: date | None = None,
    effort: Effort | None = None,
) -> Subtask:
    return Subtask(
        id=title,
        title=title,
        status=status,
        note=None,
        scheduled_on=scheduled_on,
        effort=effort,
    )


def _plan(
    *items: Subtask,
    plan_id: str,
    created_order: int = 1,
    priority: Priority | None = None,
    goal: str | None = None,
) -> Plan:
    return Plan(
        id=plan_id,
        goal=plan_id if goal is None else goal,
        subtasks=items,
        created_order=created_order,
        version=0,
        priority=priority,
    )


def test_day_budget_is_eight_for_every_date() -> None:
    assert day_budget(date(2020, 1, 1)) == 8
    assert day_budget(_TODAY) == 8
    assert day_budget(date(2027, 12, 31)) == 8


def test_task_hours_are_one_three_six_and_missing_is_three() -> None:
    assert task_hours(_item("S", effort=Effort.S)) == 1
    assert task_hours(_item("M", effort=Effort.M)) == 3
    assert task_hours(_item("L", effort=Effort.L)) == 6
    assert task_hours(_item("Thiếu")) == 3


def test_done_and_skipped_add_zero() -> None:
    done = _item("Xong", status=SubtaskStatus.DONE, effort=Effort.L, scheduled_on=_TODAY)
    skipped = _item(
        "Bỏ",
        status=SubtaskStatus.SKIPPED,
        effort=Effort.L,
        scheduled_on=_TODAY,
    )
    assert task_hours(done) == 0
    assert task_hours(skipped) == 0
    load = day_load((_plan(done, skipped, plan_id="một"),), _TODAY, _TODAY)
    assert load == DayLoad(total=0, provisional=0)


def test_past_day_load_is_zero() -> None:
    past = _TODAY.replace(day=9)
    item = _item("Cũ", effort=Effort.L, scheduled_on=past)
    plans = (_plan(item, plan_id="một"),)
    assert day_load(plans, past, _TODAY) == DayLoad(total=0, provisional=0)
    assert day_load(plans, _TODAY, _TODAY) == DayLoad(total=0, provisional=0)


def test_today_load_counts() -> None:
    plans = (
        _plan(_item("M", effort=Effort.M, scheduled_on=_TODAY), plan_id="một"),
        _plan(_item("S", effort=Effort.S, scheduled_on=_TODAY), plan_id="hai"),
        _plan(_item("Thiếu", scheduled_on=_TODAY), plan_id="ba"),
        _plan(_item("Mai", effort=Effort.L, scheduled_on=_DAY), plan_id="bốn"),
    )
    assert day_load(plans, _TODAY, _TODAY) == DayLoad(total=7, provisional=1)


def test_equal_budget_is_not_overload() -> None:
    plans = (
        _plan(
            _item("L", effort=Effort.L, scheduled_on=_DAY),
            _item("S1", effort=Effort.S, scheduled_on=_DAY),
            _item("S2", effort=Effort.S, scheduled_on=_DAY),
            plan_id="một",
        ),
    )
    load = day_load(plans, _DAY, _TODAY)
    assert load.total == 8
    assert not load.total > day_budget(_DAY)
    assert propose_load_moves(plans, _DAY, _TODAY) == ()


def test_move_order_low_then_empty_with_medium_then_high() -> None:
    def one(name: str, order: int, priority: Priority | None) -> Plan:
        return _plan(
            _item(name, effort=Effort.L, scheduled_on=_DAY),
            plan_id=name,
            created_order=order,
            priority=priority,
            goal=name,
        )

    low = one("Thấp", 9, Priority.LOW)
    empty = one("Trống", 2, None)
    medium = one("Vừa", 3, Priority.MEDIUM)
    high = one("Cao", 1, Priority.HIGH)
    moves = propose_load_moves((high, empty, medium, low), _DAY, _TODAY)
    assert [item.subtask_id for item in moves] == ["Thấp", "Trống", "Vừa"]


def test_same_plan_later_stored_order_moves_first() -> None:
    earlier = _item("Trước", effort=Effort.L, scheduled_on=_DAY)
    later = _item("Sau", effort=Effort.S, scheduled_on=_DAY)
    incoming = _item("Mới", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(earlier, later, incoming, plan_id="một", priority=Priority.LOW)
    moves = propose_load_moves((plan,), _DAY, _TODAY, incoming=(("một", "Mới"),))
    assert [item.subtask_id for item in moves] == ["Sau", "Trước"]


def test_destination_is_nearest_day_within_seven() -> None:
    full = _item("Đầy", effort=Effort.L, scheduled_on=_DAY.replace(day=13))
    candidate = _item("Dời", effort=Effort.L, scheduled_on=_DAY)
    incoming = _item("Mới", effort=Effort.L, scheduled_on=_DAY)
    plans = (
        _plan(candidate, incoming, plan_id="một", priority=Priority.LOW),
        _plan(full, plan_id="hai"),
    )
    moves = propose_load_moves(plans, _DAY, _TODAY, incoming=(("một", "Mới"),))
    assert [(item.subtask_id, item.scheduled_on) for item in moves] == [
        ("Dời", date(2026, 11, 14))
    ]


def test_no_room_in_seven_days_stays() -> None:
    blocked = [
        _item(f"Ngày {offset}", effort=Effort.L, scheduled_on=_DAY.replace(day=12 + offset))
        for offset in range(1, 8)
    ]
    staying = _item("Ở lại", effort=Effort.L, scheduled_on=_DAY)
    incoming = _item("Mới", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(staying, incoming, *blocked, plan_id="một", priority=Priority.LOW)
    moves = propose_load_moves((plan,), _DAY, _TODAY, incoming=(("một", "Mới"),))
    assert moves == ()
    assert staying.scheduled_on == _DAY


def test_newly_placed_task_is_not_a_candidate() -> None:
    old = _item("Cũ", effort=Effort.L, scheduled_on=_DAY)
    new = _item("Mới", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(old, new, plan_id="một", priority=Priority.LOW, goal="Azure")
    moves = propose_load_moves((plan,), _DAY, _TODAY, incoming=(("một", "Mới"),))
    assert [item.subtask_id for item in moves] == ["Cũ"]
    assert moves[0].goal == "Azure"
    assert moves[0].scheduled_on == date(2026, 11, 13)


def test_same_level_later_plan_deadline_moves_first() -> None:
    later_deadline = _plan(
        _item("Muộn", effort=Effort.L, scheduled_on=_DAY),
        _item("Hạn", effort=Effort.S, scheduled_on=date(2026, 11, 30)),
        plan_id="muộn",
        created_order=5,
        priority=Priority.LOW,
    )
    earlier_deadline = _plan(
        _item("Sớm", effort=Effort.L, scheduled_on=_DAY),
        plan_id="sớm",
        created_order=1,
        priority=Priority.LOW,
    )
    moves = propose_load_moves((earlier_deadline, later_deadline), _DAY, _TODAY)
    assert [item.subtask_id for item in moves] == ["Muộn"]


def test_same_level_and_deadline_earlier_created_plan_moves_first() -> None:
    first = _plan(
        _item("Trước", effort=Effort.L, scheduled_on=_DAY),
        plan_id="trước",
        created_order=1,
        priority=Priority.LOW,
    )
    second = _plan(
        _item("Sau", effort=Effort.L, scheduled_on=_DAY),
        plan_id="sau",
        created_order=5,
        priority=Priority.LOW,
    )
    moves = propose_load_moves((second, first), _DAY, _TODAY)
    assert [item.subtask_id for item in moves] == ["Trước"]


def test_empty_priority_stays_empty_after_ordering() -> None:
    plan = _plan(
        _item("Trống", effort=Effort.L, scheduled_on=_DAY),
        _item("Mới", effort=Effort.L, scheduled_on=_DAY),
        plan_id="trống",
        priority=None,
    )
    moves = propose_load_moves((plan,), _DAY, _TODAY, incoming=(("trống", "Mới"),))
    assert [item.subtask_id for item in moves] == ["Trống"]
    assert plan.priority is None


def test_earlier_proposed_moves_count_toward_destination() -> None:
    first = _item("Đầu", effort=Effort.L, scheduled_on=_DAY)
    middle = _item("Giữa", effort=Effort.L, scheduled_on=_DAY)
    last = _item("Cuối", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(first, middle, last, plan_id="thấp", priority=Priority.LOW)
    moves = propose_load_moves((plan,), _DAY, _TODAY)
    assert [(item.subtask_id, item.scheduled_on) for item in moves] == [
        ("Cuối", date(2026, 11, 13)),
        ("Giữa", date(2026, 11, 14)),
    ]


def test_no_prefix_clears_the_day_proposes_nothing() -> None:
    old = _item("Cũ", effort=Effort.S, scheduled_on=_DAY)
    first_new = _item("Mới một", effort=Effort.L, scheduled_on=_DAY)
    second_new = _item("Mới hai", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(old, first_new, second_new, plan_id="một")
    moves = propose_load_moves(
        (plan,),
        _DAY,
        _TODAY,
        incoming=(("một", "Mới một"), ("một", "Mới hai")),
    )
    assert moves == ()


def test_reserved_hours_count_toward_destination() -> None:
    old = _item("Cũ", effort=Effort.L, scheduled_on=_DAY)
    new = _item("Mới", effort=Effort.L, scheduled_on=_DAY)
    plan = _plan(old, new, plan_id="một", priority=Priority.LOW)
    moves = propose_load_moves(
        (plan,),
        _DAY,
        _TODAY,
        incoming=(("một", "Mới"),),
        reserved={date(2026, 11, 13): 6},
    )
    assert [(item.subtask_id, item.scheduled_on) for item in moves] == [
        ("Cũ", date(2026, 11, 14)),
    ]
