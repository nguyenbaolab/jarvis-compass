"""User Story 1: create_plan lưu kế hoạch hoặc từ chối cả yêu cầu."""

import json
import re
import unicodedata

import pytest

from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import create_plan

_PLAN_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _plan(result: ToolResult) -> dict:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"id", "goal", "subtasks"}
    assert _PLAN_ID.fullmatch(data["id"])
    seen: set[str] = set()
    for item in data["subtasks"]:
        assert list(item) == ["id", "title", "status"]
        assert isinstance(item["title"], str)
        assert item["status"] == "pending"
        assert _PLAN_ID.fullmatch(item["id"])
        assert item["id"] != data["id"]
        assert item["id"] not in seen
        seen.add(item["id"])
    return data


def test_create_returns_goal_and_ordered_subtasks() -> None:
    store = MemoryPlanStore()
    data = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    assert data["goal"] == "Học tiếng Nhật"
    assert [item["title"] for item in data["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert len(store.list_newest_first()) == 1


def test_omitted_subtasks_are_empty() -> None:
    store = MemoryPlanStore()
    data = _plan(create_plan("Viết báo cáo", store=store))
    assert data["goal"] == "Viết báo cáo"
    assert data["subtasks"] == []


def test_empty_subtask_list_is_empty() -> None:
    store = MemoryPlanStore()
    data = _plan(create_plan("Viết báo cáo", [], store=store))
    assert data["subtasks"] == []


def test_same_content_creates_two_plans() -> None:
    store = MemoryPlanStore()
    first = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    second = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    assert first["id"] != second["id"]
    stored = store.list_newest_first()
    assert {plan.id for plan in stored} == {first["id"], second["id"]}


def test_strip_ends_and_keep_inner_spaces() -> None:
    store = MemoryPlanStore()
    data = _plan(create_plan("  Học  tiếng Nhật  ", ["  Học  hiragana  "], store=store))
    assert data["goal"] == "Học  tiếng Nhật"
    assert [item["title"] for item in data["subtasks"]] == ["Học  hiragana"]


def test_duplicate_subtask_titles_stay_in_place() -> None:
    store = MemoryPlanStore()
    data = _plan(create_plan("Ôn bài", ["Đọc", "Đọc"], store=store))
    assert [item["title"] for item in data["subtasks"]] == ["Đọc", "Đọc"]


def test_goal_and_title_are_stored_as_nfc() -> None:
    store = MemoryPlanStore()
    nfd_goal = unicodedata.normalize("NFD", "Học tiếng Nhật")
    nfd_title = unicodedata.normalize("NFD", "Học hiragana")
    data = _plan(create_plan(nfd_goal, [nfd_title], store=store))
    assert data["goal"] == unicodedata.normalize("NFC", "Học tiếng Nhật")
    assert [item["title"] for item in data["subtasks"]] == [
        unicodedata.normalize("NFC", "Học hiragana")
    ]


@pytest.mark.parametrize("goal", [None, "", "   "])
def test_blank_goal_is_rejected_and_store_stays(goal: str | None) -> None:
    store = MemoryPlanStore()
    create_plan("Đã có một", store=store)
    create_plan("Đã có hai", store=store)
    with pytest.raises(ToolError):
        create_plan(goal, ["việc"], store=store)
    assert len(store.list_newest_first()) == 2


def test_blank_subtask_rejects_whole_request() -> None:
    store = MemoryPlanStore()
    create_plan("Đã có", ["cũ"], store=store)
    with pytest.raises(ToolError):
        create_plan("Mới", ["Học hiragana", "   ", "Luyện"], store=store)
    with pytest.raises(ToolError):
        create_plan("Mới", ["", "Học hiragana"], store=store)
    stored = store.list_newest_first()
    assert len(stored) == 1
    assert stored[0].goal == "Đã có"
