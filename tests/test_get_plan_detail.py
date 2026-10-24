"""get_plan_detail mở đúng kế hoạch, hoặc từ chối khi danh tính không dùng được."""

import asyncio

import pytest

from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.helpers import listed_plans, pending_plan
from tools.base import ToolError
from tools.plan_tools import create_plan, get_plan_detail

_MISSING = "Không có kế hoạch với danh tính này."
_BLANK = "Danh tính kế hoạch chưa được đưa."


def test_open_returns_goal_and_ordered_subtasks() -> None:
    store = MemoryPlanStore()
    created = pending_plan(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        ))
    )
    opened = pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert opened == created


def test_open_plan_without_subtasks() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Viết báo cáo", store=store)))
    opened = pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert opened["goal"] == "Viết báo cáo"
    assert opened["subtasks"] == []


def test_open_middle_plan_among_three() -> None:
    store = MemoryPlanStore()
    first = pending_plan(asyncio.run(create_plan("A", ["a1"], store=store)))
    middle = pending_plan(asyncio.run(create_plan("B", ["b1", "b2"], store=store)))
    last = pending_plan(asyncio.run(create_plan("C", ["c1"], store=store)))
    opened = pending_plan(asyncio.run(get_plan_detail(middle["id"], store=store)))
    assert opened == middle
    assert opened != first
    assert opened != last


def test_open_matches_the_same_plan_in_the_list() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    opened = pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    listed = next(item for item in listed_plans(store) if item["id"] == created["id"])
    assert opened == listed


def test_surrounding_whitespace_still_opens() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    opened = pending_plan(asyncio.run(get_plan_detail(f"  {created['id']}  ", store=store)))
    assert opened == created


def test_open_same_id_twice() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    first = pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    second = pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert first == second == created


def test_successful_open_does_not_change_the_list() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    pending_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert listed_plans(store) == before


def _refusal(plan_id: str | None, store: MemoryPlanStore) -> str:
    with pytest.raises(ToolError) as caught:
        asyncio.run(get_plan_detail(plan_id, store=store))
    return str(caught.value)


def _upper_id(plan_id: str) -> str:
    changed = plan_id.upper()
    assert changed != plan_id
    return changed


def test_uppercase_id_is_missing() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert _refusal(_upper_id(created["id"]), store) == _MISSING
    assert listed_plans(store) == before
    assert pending_plan(asyncio.run(get_plan_detail(created["id"], store=store))) == created


def test_goal_is_not_an_id() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert _refusal("Học tiếng Nhật", store) == _MISSING
    assert listed_plans(store) == before


def test_goal_fragment_is_not_an_id() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert _refusal("tiếng Nhật", store) == _MISSING
    assert listed_plans(store) == before
    assert pending_plan(asyncio.run(get_plan_detail(created["id"], store=store))) == created


def test_list_positions_are_not_ids() -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    pending_plan(asyncio.run(create_plan("Viết báo cáo", store=store)))
    before = listed_plans(store)
    assert _refusal("1", store) == _MISSING
    assert _refusal("2", store) == _MISSING
    assert listed_plans(store) == before
    assert pending_plan(asyncio.run(get_plan_detail(created["id"], store=store))) == created


@pytest.mark.parametrize("plan_id", [None, "", "   ", "\t\n"])
def test_blank_id_is_rejected(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    created = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert _refusal(plan_id, store) == _BLANK
    assert _BLANK != _MISSING
    assert listed_plans(store) == before
    assert len(asyncio.run(store.list_newest_first())) == 1
    assert pending_plan(asyncio.run(get_plan_detail(created["id"], store=store))) == created
