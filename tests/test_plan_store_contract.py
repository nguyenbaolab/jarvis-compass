"""Cùng các ca cổng trên bản bộ nhớ và trên Supabase."""

import asyncio
import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from core.plans import (
    Effort,
    Plan,
    PlanConflictError,
    PlanDomainError,
    PlanStore,
    Priority,
    Subtask,
    SubtaskStatus,
)
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.helpers import _UUID
from tools.base import TurnContext
from tools.plan_tools import add_subtask

_STAMP = datetime(2026, 11, 6, 8, 0, tzinfo=timezone(timedelta(hours=2)))
_DAY = date(2026, 11, 6)
_NEXT = date(2026, 11, 7)


def _subtask(
    title: str,
    *,
    status: SubtaskStatus = SubtaskStatus.PENDING,
    note: str | None = None,
) -> Subtask:
    return Subtask(id=str(uuid.uuid4()), title=title, status=status, note=note)


def _same_subtasks(left: tuple[Subtask, ...], right: tuple[Subtask, ...]) -> None:
    assert [(item.id, item.title, item.status, item.note) for item in left] == [
        (item.id, item.title, item.status, item.note) for item in right
    ]


async def run_contract(store: PlanStore) -> None:
    """Mọi ca cổng trên một bản store."""

    first_tasks = (_subtask("Học hiragana"), _subtask("Mua vở"))
    first = await store.add("Học tiếng Nhật", first_tasks)
    assert _UUID.fullmatch(first.id)
    assert first.goal == "Học tiếng Nhật"
    _same_subtasks(first.subtasks, first_tasks)

    second_tasks = (_subtask("Một"), _subtask("Hai"), _subtask("Ba"))
    second = await store.add("Kế hoạch sau", second_tasks)
    listed = await store.list_newest_first()
    assert [plan.id for plan in listed] == [second.id, first.id]
    assert listed[0].created_order > listed[1].created_order

    opened = await store.get(first.id)
    assert opened is not None
    assert opened.id == first.id
    assert opened.goal == first.goal
    _same_subtasks(opened.subtasks, first_tasks)
    other = str(uuid.uuid4())
    assert other != first.id
    assert other != second.id
    assert await store.get(other) is None
    assert await store.get("1") is None
    assert await store.get("2") is None
    again = await store.list_newest_first()
    assert [plan.id for plan in again] == [second.id, first.id]

    viet_tasks = (_subtask("Học hiragana"), _subtask("Nghe hội thoại"), _subtask("Đọc bảng"))
    viet = await store.add("Học tiếng Nhật", viet_tasks)
    from_list = await store.list_newest_first()
    found = next(plan for plan in from_list if plan.id == viet.id)
    opened_viet = await store.get(viet.id)
    assert opened_viet is not None
    assert found.goal == "Học tiếng Nhật"
    assert opened_viet.goal == "Học tiếng Nhật"
    assert [item.title for item in found.subtasks] == [item.title for item in viet_tasks]
    assert [item.title for item in opened_viet.subtasks] == [item.title for item in viet_tasks]
    await _case_edit(store)
    await _case_missing(store)
    await _case_drop_subtask(store)
    await _case_replace_goal(store)
    await _case_reorder_insert(store)
    await _case_add_empty(store)
    await _case_get_uppercase(store)


async def _case_edit(store: PlanStore) -> None:
    """Ca 5: đổi trạng thái, thêm việc, đặt rồi xóa ghi chú."""

    kept = _subtask("Giữ nguyên")
    changing = _subtask("Đổi trạng thái")
    plan = await store.add("Sửa việc", (kept, changing))
    current = plan
    for status in (SubtaskStatus.DONE, SubtaskStatus.SKIPPED, SubtaskStatus.PENDING):
        updated = (
            current.subtasks[0],
            replace(current.subtasks[1], status=status),
        )
        await store.replace(
            Plan(
                id=current.id,
                goal=current.goal,
                subtasks=updated,
                created_order=current.created_order,
                version=current.version,
            )
        )
        opened = await store.get(current.id)
        assert opened is not None
        assert opened.subtasks[0] == kept
        assert opened.subtasks[1].status is status
        assert opened.subtasks[1].id == changing.id
        current = opened
    extra = _subtask("Mua giáo trình")
    await store.replace(
        Plan(
            id=current.id,
            goal=current.goal,
            subtasks=current.subtasks + (extra,),
            created_order=current.created_order,
            version=current.version,
        )
    )
    opened = await store.get(current.id)
    assert opened is not None
    assert opened.subtasks[-1].title == "Mua giáo trình"
    assert opened.subtasks[-1].status is SubtaskStatus.PENDING
    assert opened.subtasks[-1].note is None
    assert [item.id for item in opened.subtasks[:-1]] == [kept.id, changing.id]
    noted = replace(opened.subtasks[0], note="Đợi giáo trình")
    await store.replace(
        Plan(
            id=opened.id,
            goal=opened.goal,
            subtasks=(noted,) + opened.subtasks[1:],
            created_order=opened.created_order,
            version=opened.version,
        )
    )
    with_note = await store.get(opened.id)
    assert with_note is not None
    assert with_note.subtasks[0].note == "Đợi giáo trình"
    cleared = replace(with_note.subtasks[0], note=None)
    await store.replace(
        Plan(
            id=with_note.id,
            goal=with_note.goal,
            subtasks=(cleared,) + with_note.subtasks[1:],
            created_order=with_note.created_order,
            version=with_note.version,
        )
    )
    final = await store.get(with_note.id)
    assert final is not None
    assert final.subtasks[0].note is None
    assert final.subtasks[0].note != ""


_MISSING = "Không có kế hoạch với danh tính này."


async def _case_missing(store: PlanStore) -> None:
    """Ca 4: replace một id không có, gồm 1, 2, và UUID viết hoa."""

    before = await store.list_newest_first()
    assert before
    kept = before[0]
    missing_id = str(uuid.uuid4())
    assert missing_id not in {plan.id for plan in before}
    candidates = (
        missing_id,
        "1",
        "2",
        kept.id.upper(),
    )
    for plan_id in candidates:
        with pytest.raises(PlanDomainError) as caught:
            await store.replace(
                Plan(
                    id=plan_id,
                    goal="Không tạo",
                    subtasks=(),
                    created_order=kept.created_order,
                    version=0,
                )
            )
        assert str(caught.value) == _MISSING
    after = await store.list_newest_first()
    assert [plan.id for plan in after] == [plan.id for plan in before]
    again = await store.get(kept.id)
    assert again is not None
    assert again.goal == kept.goal
    _same_subtasks(again.subtasks, kept.subtasks)
    assert await store.get("1") is None
    assert await store.get("2") is None


async def _case_drop_subtask(store: PlanStore) -> None:
    """replace bớt một việc: việc bỏ không còn, việc còn giữ id và thứ tự."""

    kept = _subtask("Còn lại")
    dropped = _subtask("Bỏ đi")
    plan = await store.add("Bớt việc", (kept, dropped))
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(kept,),
            created_order=plan.created_order,
            version=plan.version,
        )
    )
    opened = await store.get(plan.id)
    assert opened is not None
    assert [item.id for item in opened.subtasks] == [kept.id]
    listed = await store.list_newest_first()
    found = next(item for item in listed if item.id == plan.id)
    assert [item.id for item in found.subtasks] == [kept.id]
    assert all(item.id != dropped.id for item in found.subtasks)


async def _case_replace_goal(store: PlanStore) -> None:
    """replace đổi goal. id và created_order giữ nguyên."""

    plan = await store.add("Mục tiêu cũ", (_subtask("Một"),))
    await store.replace(
        Plan(
            id=plan.id,
            goal="Mục tiêu mới",
            subtasks=plan.subtasks,
            created_order=plan.created_order,
            version=plan.version,
        )
    )
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.id == plan.id
    assert opened.goal == "Mục tiêu mới"
    assert opened.created_order == plan.created_order
    found = next(item for item in await store.list_newest_first() if item.id == plan.id)
    assert found.goal == "Mục tiêu mới"
    assert found.id == plan.id
    assert found.created_order == plan.created_order


async def _case_reorder_insert(store: PlanStore) -> None:
    """Đảo hai việc và chèn việc mới vào giữa. Liệt kê và mở cùng thứ tự."""

    first = _subtask("Đầu")
    second = _subtask("Cuối")
    plan = await store.add("Đảo thứ tự", (first, second))
    middle = _subtask("Giữa")
    order = (second.id, middle.id, first.id)
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(second, middle, first),
            created_order=plan.created_order,
            version=plan.version,
        )
    )
    opened = await store.get(plan.id)
    assert opened is not None
    assert [item.id for item in opened.subtasks] == list(order)
    found = next(item for item in await store.list_newest_first() if item.id == plan.id)
    assert [item.id for item in found.subtasks] == list(order)


async def _case_add_empty(store: PlanStore) -> None:
    """add không có việc con thì lần đọc có subtasks rỗng."""

    plan = await store.add("Không việc", ())
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.subtasks == ()
    found = next(item for item in await store.list_newest_first() if item.id == plan.id)
    assert found.subtasks == ()


async def _case_get_uppercase(store: PlanStore) -> None:
    """get id viết hoa của kế hoạch đang có trả None."""

    plan = await store.add("Chữ hoa", (_subtask("Một"),))
    assert plan.id != plan.id.upper()
    assert await store.get(plan.id.upper()) is None
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.id == plan.id


def _memory_store() -> MemoryPlanStore:
    return MemoryPlanStore()


async def _supabase_store() -> PlanStore:
    from tests.supabase_plan_db import prepare_local_source

    source = await prepare_local_source()
    from db.plan_store import SupabasePlanStore

    return SupabasePlanStore(source)


@pytest.fixture(params=["memory", "supabase"])
def plan_store(request: pytest.FixtureRequest) -> PlanStore:
    if request.param == "memory":
        return _memory_store()
    return asyncio.run(_supabase_store())


def test_plan_store_contract(plan_store: PlanStore) -> None:
    asyncio.run(run_contract(plan_store))


def _written(plan: Plan, *, goal: str | None = None, subtasks: tuple[Subtask, ...] | None = None) -> Plan:
    return Plan(
        id=plan.id,
        goal=plan.goal if goal is None else goal,
        subtasks=plan.subtasks if subtasks is None else subtasks,
        created_order=plan.created_order,
        version=plan.version,
        priority=plan.priority,
    )


async def _overlap_and_follow(store: PlanStore) -> None:
    """Đọc-đọc-ghi từ chối. Không chồng thì cả hai việc còn. Hai kế hoạch đều ghi được."""

    origin = await store.add("Gốc", (_subtask("Việc gốc"),))
    read_a = await store.get(origin.id)
    read_b = await store.get(origin.id)
    assert read_a is not None
    assert read_b is not None
    await store.replace(_written(read_a, goal="A đã ghi"))
    with pytest.raises(PlanConflictError):
        await store.replace(_written(read_b, goal="B ghi đè"))
    kept = await store.get(origin.id)
    assert kept is not None
    assert kept.goal == "A đã ghi"
    _same_subtasks(kept.subtasks, read_a.subtasks)

    matched = await store.get(origin.id)
    assert matched is not None
    await store.replace(_written(matched, goal="Khớp"))
    after = await store.get(origin.id)
    assert after is not None
    assert after.version == matched.version + 1
    assert after.goal == "Khớp"

    base = await store.add("Cả hai", ())
    earlier = await store.get(base.id)
    assert earlier is not None
    left = _subtask("Việc trái")
    await store.replace(_written(earlier, subtasks=(left,)))
    later = await store.get(base.id)
    assert later is not None
    right = _subtask("Việc phải")
    await store.replace(_written(later, subtasks=later.subtasks + (right,)))
    both = await store.get(base.id)
    assert both is not None
    assert [item.title for item in both.subtasks] == ["Việc trái", "Việc phải"]

    one = await store.add("Một", (_subtask("X"),))
    two = await store.add("Hai", (_subtask("Y"),))
    await store.replace(_written(one, goal="Một mới"))
    await store.replace(_written(two, goal="Hai mới"))
    opened_one = await store.get(one.id)
    opened_two = await store.get(two.id)
    assert opened_one is not None
    assert opened_two is not None
    assert opened_one.goal == "Một mới"
    assert opened_two.goal == "Hai mới"
    _same_subtasks(opened_one.subtasks, one.subtasks)
    _same_subtasks(opened_two.subtasks, two.subtasks)


def test_overlap_rejects_and_follow_up_keeps_both(plan_store: PlanStore) -> None:
    asyncio.run(_overlap_and_follow(plan_store))


def test_plan_without_version_is_type_error() -> None:
    with pytest.raises(TypeError):
        Plan(id="1", goal="Mục tiêu", subtasks=(), created_order=1)


def test_plan_conflict_error_is_not_domain_error() -> None:
    from core.plans import PlanConflictError

    assert not issubclass(PlanConflictError, PlanDomainError)


def _dated(title: str, day: date | None) -> Subtask:
    return Subtask(
        id=str(uuid.uuid4()),
        title=title,
        status=SubtaskStatus.PENDING,
        note=None,
        scheduled_on=day,
    )


def _saved(plan: Plan, subtasks: tuple[Subtask, ...]) -> Plan:
    return Plan(
        id=plan.id,
        goal=plan.goal,
        subtasks=subtasks,
        created_order=plan.created_order,
        version=plan.version,
        priority=plan.priority,
    )


async def _history(store: PlanStore, plan_id: str, subtask_id: str) -> list[object]:
    if isinstance(store, MemoryPlanStore):
        return [
            row
            for row in store.date_moves
            if row.plan_id == plan_id and row.subtask_id == subtask_id
        ]
    from db.client import postgrest_client
    from tests.supabase_plan_db import read_test_env

    url, key = read_test_env()
    async with postgrest_client(url, key) as client:
        response = await (
            client.from_("subtask_date_moves")
            .select("id,plan_id,subtask_id,from_date,to_date")
            .eq("plan_id", plan_id)
            .eq("subtask_id", subtask_id)
            .execute()
        )
    rows = response.data
    if not isinstance(rows, list):
        raise AssertionError("lịch sử không phải mảng")
    return rows


def test_date_to_other_date_writes_one_history_row(plan_store: PlanStore) -> None:
    asyncio.run(_date_to_other_date_writes_one_history_row(plan_store))


async def _date_to_other_date_writes_one_history_row(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    moved = replace(item, scheduled_on=_NEXT)
    await store.replace(_saved(plan, (moved,)), move_reason="bận", moved_at=_STAMP)
    assert len(await _history(store, plan.id, item.id)) == 1


def test_empty_to_date_writes_no_history_row(plan_store: PlanStore) -> None:
    asyncio.run(_empty_to_date_writes_no_history_row(plan_store))


async def _empty_to_date_writes_no_history_row(store: PlanStore) -> None:
    item = _dated("Việc", None)
    plan = await store.add("Mục tiêu", (item,))
    await store.replace(_saved(plan, (replace(item, scheduled_on=_DAY),)), moved_at=_STAMP)
    assert await _history(store, plan.id, item.id) == []


def test_date_to_empty_writes_no_history_row(plan_store: PlanStore) -> None:
    asyncio.run(_date_to_empty_writes_no_history_row(plan_store))


async def _date_to_empty_writes_no_history_row(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    await store.replace(_saved(plan, (replace(item, scheduled_on=None),)))
    assert await _history(store, plan.id, item.id) == []


def test_same_date_writes_no_history_row(plan_store: PlanStore) -> None:
    asyncio.run(_same_date_writes_no_history_row(plan_store))


async def _same_date_writes_no_history_row(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    await store.replace(_saved(plan, (replace(item, title="Việc sửa"),)), moved_at=_STAMP)
    assert await _history(store, plan.id, item.id) == []


def test_several_date_changes_write_one_row_each(plan_store: PlanStore) -> None:
    asyncio.run(_several_date_changes_write_one_row_each(plan_store))


async def _several_date_changes_write_one_row_each(store: PlanStore) -> None:
    first = _dated("Một", _DAY)
    second = _dated("Hai", _DAY)
    plan = await store.add("Mục tiêu", (first, second))
    await store.replace(
        _saved(plan, (replace(first, scheduled_on=_NEXT), replace(second, scheduled_on=_NEXT))),
        move_reason=None,
        moved_at=_STAMP,
    )
    assert len(await _history(store, plan.id, first.id)) == 1
    assert len(await _history(store, plan.id, second.id)) == 1


def test_version_conflict_keeps_dates_and_writes_no_row(plan_store: PlanStore) -> None:
    asyncio.run(_version_conflict_keeps_dates_and_writes_no_row(plan_store))


async def _version_conflict_keeps_dates_and_writes_no_row(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    await store.replace(_saved(plan, (replace(item, title="Đã ghi"),)))
    with pytest.raises(PlanConflictError):
        await store.replace(
            _saved(plan, (replace(item, scheduled_on=_NEXT),)),
            moved_at=_STAMP,
        )
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.subtasks[0].scheduled_on == _DAY
    assert await _history(store, plan.id, item.id) == []


def test_null_moved_at_on_date_change_errors_and_keeps_plan(plan_store: PlanStore) -> None:
    asyncio.run(_null_moved_at_on_date_change_errors_and_keeps_plan(plan_store))


async def _null_moved_at_on_date_change_errors_and_keeps_plan(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    with pytest.raises(PlanDomainError):
        await store.replace(_saved(plan, (replace(item, scheduled_on=_NEXT),)))
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.subtasks[0].scheduled_on == _DAY
    assert opened.version == plan.version
    assert await _history(store, plan.id, item.id) == []


def test_dropped_subtask_keeps_its_history(plan_store: PlanStore) -> None:
    asyncio.run(_dropped_subtask_keeps_its_history(plan_store))


async def _dropped_subtask_keeps_its_history(store: PlanStore) -> None:
    item = _dated("Việc", _DAY)
    plan = await store.add("Mục tiêu", (item,))
    await store.replace(_saved(plan, (replace(item, scheduled_on=_NEXT),)), moved_at=_STAMP)
    current = await store.get(plan.id)
    assert current is not None
    await store.replace(_saved(current, ()))
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.subtasks == ()
    assert len(await _history(store, plan.id, item.id)) == 1


def test_add_returns_priority_date_and_effort(plan_store: PlanStore) -> None:
    asyncio.run(_add_returns_priority_date_and_effort(plan_store))


async def _add_returns_priority_date_and_effort(store: PlanStore) -> None:
    item = Subtask(
        id=str(uuid.uuid4()),
        title="Việc",
        status=SubtaskStatus.PENDING,
        note=None,
        scheduled_on=_DAY,
        effort=Effort.M,
    )
    plan = await store.add("Mục tiêu", (item,), priority=Priority.HIGH)
    assert plan.priority is Priority.HIGH
    assert plan.subtasks[0].scheduled_on == _DAY
    assert plan.subtasks[0].effort is Effort.M


def _with_effort(title: str, day: date | None, effort: Effort | None) -> Subtask:
    return Subtask(
        id=str(uuid.uuid4()),
        title=title,
        status=SubtaskStatus.PENDING,
        note=None,
        scheduled_on=day,
        effort=effort,
    )


def test_replace_adds_new_subtask_with_date_and_effort(plan_store: PlanStore) -> None:
    asyncio.run(_replace_adds_new_subtask_with_date_and_effort(plan_store))


async def _replace_adds_new_subtask_with_date_and_effort(store: PlanStore) -> None:
    existing = _dated("Cũ", None)
    plan = await store.add("Mục tiêu", (existing,))
    added = _with_effort("Mới", _DAY, Effort.M)
    await store.replace(_saved(plan, (existing, added)))
    opened = await store.get(plan.id)
    assert opened is not None
    found = next(item for item in opened.subtasks if item.id == added.id)
    assert found.scheduled_on == _DAY
    assert found.effort is Effort.M


def test_replace_adds_new_subtask_without_date_or_effort_keeps_them_empty(plan_store: PlanStore) -> None:
    asyncio.run(_replace_adds_new_subtask_without_date_or_effort_keeps_them_empty(plan_store))


async def _replace_adds_new_subtask_without_date_or_effort_keeps_them_empty(store: PlanStore) -> None:
    existing = _dated("Cũ", _DAY)
    plan = await store.add("Mục tiêu", (existing,))
    added = _with_effort("Mới", None, None)
    await store.replace(_saved(plan, (existing, added)))
    opened = await store.get(plan.id)
    assert opened is not None
    kept = next(item for item in opened.subtasks if item.id == existing.id)
    found = next(item for item in opened.subtasks if item.id == added.id)
    assert kept.scheduled_on == _DAY
    assert found.scheduled_on is None
    assert found.effort is None


def test_new_subtask_with_date_writes_no_history_row(plan_store: PlanStore) -> None:
    asyncio.run(_new_subtask_with_date_writes_no_history_row(plan_store))


async def _new_subtask_with_date_writes_no_history_row(store: PlanStore) -> None:
    existing = _dated("Cũ", _DAY)
    plan = await store.add("Mục tiêu", (existing,))
    added = _with_effort("Mới", _NEXT, Effort.S)
    await store.replace(_saved(plan, (existing, added)), moved_at=_STAMP)
    assert await _history(store, plan.id, added.id) == []
    assert await _history(store, plan.id, existing.id) == []


def test_two_moves_on_one_plan_keep_both_destinations(plan_store: PlanStore) -> None:
    asyncio.run(_two_moves_on_one_plan_keep_both_destinations(plan_store))


async def _two_moves_on_one_plan_keep_both_destinations(store: PlanStore) -> None:
    """Hai lần replace của cùng kế hoạch giữ cả hai ngày đích và đúng hai dòng lịch sử."""

    first = _dated("Một", date(2026, 11, 8))
    second = _dated("Hai", date(2026, 11, 8))
    target = await store.add("Đích", (first, second))
    owner = await store.add("Chủ", ())
    await add_subtask(
        owner.id,
        "Xin",
        scheduled_on="2026-11-07",
        effort="S",
        confirm=True,
        load_moves=[
            {"plan_id": target.id, "subtask_id": first.id, "scheduled_on": "2026-11-09"},
            {"plan_id": target.id, "subtask_id": second.id, "scheduled_on": "2026-11-10"},
        ],
        store=store,
        turn=TurnContext(instant=_STAMP),
    )
    opened = await store.get(target.id)
    assert opened is not None
    by_id = {item.id: item.scheduled_on for item in opened.subtasks}
    assert (
        by_id[first.id],
        by_id[second.id],
        len(await _history(store, target.id, first.id)),
        len(await _history(store, target.id, second.id)),
    ) == (date(2026, 11, 9), date(2026, 11, 10), 1, 1)


def test_owner_add_and_one_move_on_the_same_plan(plan_store: PlanStore) -> None:
    asyncio.run(_owner_add_and_one_move_on_the_same_plan(plan_store))


async def _owner_add_and_one_move_on_the_same_plan(store: PlanStore) -> None:
    """Việc vừa thêm không có lịch sử. Việc dời cùng kế hoạch có đúng một dòng."""

    existing = _dated("Cũ", date(2026, 11, 8))
    plan = await store.add("Một", (existing,))
    await add_subtask(
        plan.id,
        "Mới",
        scheduled_on="2026-11-07",
        effort="S",
        confirm=True,
        load_moves=[
            {"plan_id": plan.id, "subtask_id": existing.id, "scheduled_on": "2026-11-09"},
        ],
        store=store,
        turn=TurnContext(instant=_STAMP),
    )
    opened = await store.get(plan.id)
    assert opened is not None
    added = next(item for item in opened.subtasks if item.title == "Mới")
    moved = next(item for item in opened.subtasks if item.id == existing.id)
    assert added.scheduled_on == date(2026, 11, 7)
    assert await _history(store, plan.id, added.id) == []
    assert moved.scheduled_on == date(2026, 11, 9)
    assert len(await _history(store, plan.id, existing.id)) == 1
