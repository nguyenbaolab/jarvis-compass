"""Cùng các ca cổng trên bản bộ nhớ và trên Supabase."""

import asyncio
import uuid
from dataclasses import replace

import pytest

from core.plans import Plan, PlanDomainError, PlanStore, Subtask, SubtaskStatus
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.helpers import _UUID


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
                Plan(id=plan_id, goal="Không tạo", subtasks=(), created_order=kept.created_order)
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
