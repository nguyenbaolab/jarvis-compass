"""User Story 1: create_plan lưu kế hoạch hoặc từ chối cả yêu cầu."""

import asyncio
import json
import unicodedata

import pytest

from core.plans import Priority
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.helpers import pending_plan
from tools.base import ToolError
from tools.plan_tools import create_plan

_BLANK_TITLE = "Việc con không được để trống."


def test_create_returns_goal_and_ordered_subtasks() -> None:
    store = MemoryPlanStore()
    data = pending_plan(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        ))
    )
    assert data["goal"] == "Học tiếng Nhật"
    assert [item["title"] for item in data["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert len(asyncio.run(store.list_newest_first())) == 1


def test_omitted_subtasks_are_empty() -> None:
    store = MemoryPlanStore()
    data = pending_plan(asyncio.run(create_plan("Viết báo cáo", store=store)))
    assert data["goal"] == "Viết báo cáo"
    assert data["subtasks"] == []


def test_empty_subtask_list_is_empty() -> None:
    store = MemoryPlanStore()
    data = pending_plan(asyncio.run(create_plan("Viết báo cáo", [], store=store)))
    assert data["subtasks"] == []


def test_same_content_creates_two_plans() -> None:
    store = MemoryPlanStore()
    first = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    second = pending_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    assert first["id"] != second["id"]
    stored = asyncio.run(store.list_newest_first())
    assert {plan.id for plan in stored} == {first["id"], second["id"]}


def test_strip_ends_and_keep_inner_spaces() -> None:
    store = MemoryPlanStore()
    data = pending_plan(asyncio.run(create_plan("  Học  tiếng Nhật  ", ["  Học  hiragana  "], store=store)))
    assert data["goal"] == "Học  tiếng Nhật"
    assert [item["title"] for item in data["subtasks"]] == ["Học  hiragana"]


def test_duplicate_subtask_titles_stay_in_place() -> None:
    store = MemoryPlanStore()
    data = pending_plan(asyncio.run(create_plan("Ôn bài", ["Đọc", "Đọc"], store=store)))
    assert [item["title"] for item in data["subtasks"]] == ["Đọc", "Đọc"]


def test_goal_and_title_are_stored_as_nfc() -> None:
    store = MemoryPlanStore()
    nfd_goal = unicodedata.normalize("NFD", "Học tiếng Nhật")
    nfd_title = unicodedata.normalize("NFD", "Học hiragana")
    data = pending_plan(asyncio.run(create_plan(nfd_goal, [nfd_title], store=store)))
    assert data["goal"] == unicodedata.normalize("NFC", "Học tiếng Nhật")
    assert [item["title"] for item in data["subtasks"]] == [
        unicodedata.normalize("NFC", "Học hiragana")
    ]


@pytest.mark.parametrize("goal", [None, "", "   "])
def test_blank_goal_is_rejected_and_store_stays(goal: str | None) -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Đã có một", store=store))
    asyncio.run(create_plan("Đã có hai", store=store))
    with pytest.raises(ToolError):
        asyncio.run(create_plan(goal, ["việc"], store=store))
    assert len(asyncio.run(store.list_newest_first())) == 2


def test_blank_subtask_rejects_whole_request() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Đã có", ["cũ"], store=store))
    with pytest.raises(ToolError):
        asyncio.run(create_plan("Mới", ["Học hiragana", "   ", "Luyện"], store=store))
    with pytest.raises(ToolError):
        asyncio.run(create_plan("Mới", ["", "Học hiragana"], store=store))
    stored = asyncio.run(store.list_newest_first())
    assert len(stored) == 1
    assert stored[0].goal == "Đã có"


def test_create_plan_rejects_none_title() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Đã có", ["cũ"], store=store))
    with pytest.raises(ToolError) as caught:
        asyncio.run(create_plan("Mới", [None], store=store))  # type: ignore[list-item]
    assert str(caught.value) == _BLANK_TITLE
    stored = asyncio.run(store.list_newest_first())
    assert len(stored) == 1
    assert stored[0].goal == "Đã có"


class _RecordingAdd(MemoryPlanStore):
    """Ghi kwargs của add. Không nhận tham số vị trí thứ ba."""

    def __init__(self) -> None:
        super().__init__()
        self.kwargs: list[dict[str, object]] = []

    async def add(self, goal: str, subtasks: tuple, **kwargs: object):  # type: ignore[override]
        self.kwargs.append(kwargs)
        if kwargs:
            return await super().add(goal, subtasks, **kwargs)  # type: ignore[arg-type]
        return await super().add(goal, subtasks)


def test_create_plan_stores_date_effort_and_priority() -> None:
    store = MemoryPlanStore()
    data = json.loads(
        asyncio.run(
            create_plan(
                "Học tiếng Nhật",
                [{"title": "Học hiragana", "scheduled_on": "2026-11-06", "effort": "M"}],
                priority="high",
                store=store,
            )
        ).output
    )
    assert data["priority"] == "high"
    assert data["subtasks"][0]["scheduled_on"] == "2026-11-06"
    assert data["subtasks"][0]["effort"] == "M"
    stored = asyncio.run(store.list_newest_first())
    assert stored[0].priority is Priority.HIGH
    assert stored[0].subtasks[0].scheduled_on.isoformat() == "2026-11-06"
    assert stored[0].subtasks[0].effort.value == "M"


def test_create_plan_without_priority_calls_add_with_two_arguments() -> None:
    store = _RecordingAdd()
    asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    assert store.kwargs == [{}]


def test_create_plan_with_priority_passes_it_to_add() -> None:
    store = _RecordingAdd()
    asyncio.run(create_plan("Học tiếng Nhật", store=store, priority="low"))
    assert store.kwargs == [{"priority": Priority.LOW}]
