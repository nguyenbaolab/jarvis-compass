"""User Story 2: get_plans liệt kê kế hoạch đang hoạt động, không lọc."""

import asyncio
import json
import unicodedata
import uuid

import pytest

from core.plans import Subtask, SubtaskStatus
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import create_plan, get_plans


def _plans(result: ToolResult) -> list[dict]:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"plans"}
    for plan in data["plans"]:
        assert set(plan) == {"id", "goal", "subtasks"}
        seen: set[str] = set()
        for item in plan["subtasks"]:
            assert list(item) == ["id", "title", "status", "note"]
            assert item["status"] == "pending"
            assert item["id"] != plan["id"]
            assert item["id"] not in seen
            seen.add(item["id"])
    return data["plans"]


def test_list_returns_the_plan_just_created() -> None:
    store = MemoryPlanStore()
    created = json.loads(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )).output
    )
    listed = _plans(asyncio.run(get_plans(store=store)))
    assert listed == [created]


def test_lists_newest_first_with_subtasks() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("A", ["a1"], store=store))
    asyncio.run(create_plan("B", ["b1", "b2"], store=store))
    asyncio.run(create_plan("C", ["c1"], store=store))
    listed = _plans(asyncio.run(get_plans(store=store)))
    assert [plan["goal"] for plan in listed] == ["C", "B", "A"]
    assert [item["title"] for item in listed[0]["subtasks"]] == ["c1"]
    assert [item["title"] for item in listed[1]["subtasks"]] == ["b1", "b2"]
    assert [item["title"] for item in listed[2]["subtasks"]] == ["a1"]


def test_same_goal_plans_both_appear() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", ["một"], store=store))
    asyncio.run(create_plan("Học tiếng Nhật", ["hai"], store=store))
    listed = _plans(asyncio.run(get_plans(store=store)))
    assert len(listed) == 2
    assert listed[0]["id"] != listed[1]["id"]
    assert listed[0]["goal"] == listed[1]["goal"] == "Học tiếng Nhật"


def test_empty_store_returns_empty_list() -> None:
    result = asyncio.run(get_plans(store=MemoryPlanStore()))
    assert result.success is True
    assert json.loads(result.output) == {"plans": []}


def test_rejected_create_does_not_grow_the_list() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Giữ", ["một"], store=store))
    before = _plans(asyncio.run(get_plans(store=store)))
    with pytest.raises(ToolError):
        asyncio.run(create_plan("   ", store=store))
    assert _plans(asyncio.run(get_plans(store=store))) == before


def test_nfd_goal_is_listed_as_nfc() -> None:
    store = MemoryPlanStore()
    nfd_goal = unicodedata.normalize("NFD", "Học tiếng Nhật")
    created = json.loads(asyncio.run(create_plan(nfd_goal, store=store)).output)
    nfc_goal = unicodedata.normalize("NFC", "Học tiếng Nhật")
    assert created["goal"] == nfc_goal
    listed = _plans(asyncio.run(get_plans(store=store)))
    assert listed[0]["goal"] == nfc_goal
    assert listed[0]["id"] == created["id"]


def test_keyword_matches_goal_not_other_plan() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    asyncio.run(create_plan("Học guitar", ["Hợp âm"], store=store))
    listed = _plans(asyncio.run(get_plans("Nhật", store=store)))
    assert len(listed) == 1
    assert listed[0]["goal"] == "Học tiếng Nhật"
    assert [item["title"] for item in listed[0]["subtasks"]] == ["Học hiragana"]


def test_keyword_tieng_and_casefold_and_padding() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    assert _plans(asyncio.run(get_plans("tiếng", store=store)))[0]["goal"] == "Học tiếng Nhật"
    assert _plans(asyncio.run(get_plans("TIẾNG", store=store)))[0]["goal"] == "Học tiếng Nhật"
    assert _plans(asyncio.run(get_plans("  Nhật  ", store=store)))[0]["goal"] == "Học tiếng Nhật"


def test_tieng_without_diacritic_does_not_match() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", store=store))
    assert _plans(asyncio.run(get_plans("tieng", store=store))) == []


def test_keyword_in_subtask_only_matches() -> None:
    store = MemoryPlanStore()
    decoy = json.loads(asyncio.run(create_plan("Học guitar", ["Hợp âm"], store=store)).output)
    matched = json.loads(
        asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana", "Mua giáo trình Nhật"], store=store)).output
    )
    listed = _plans(asyncio.run(get_plans("giáo trình", store=store)))
    assert [plan["id"] for plan in listed] == [matched["id"]]
    assert decoy["id"] not in [plan["id"] for plan in listed]
    assert [item["title"] for item in listed[0]["subtasks"]] == ["Học hiragana", "Mua giáo trình Nhật"]


def test_keyword_in_goal_and_many_titles_appears_once() -> None:
    store = MemoryPlanStore()
    decoy = json.loads(asyncio.run(create_plan("Học guitar", ["Hợp âm"], store=store)).output)
    matched = json.loads(
        asyncio.run(
            create_plan("Mua giáo trình Nhật", ["Đọc giáo trình", "Ôn giáo trình"], store=store)
        ).output
    )
    listed = _plans(asyncio.run(get_plans("giáo trình", store=store)))
    assert [plan["id"] for plan in listed] == [matched["id"]]
    assert decoy["id"] not in [plan["id"] for plan in listed]


def test_two_title_matches_stay_newest_first() -> None:
    store = MemoryPlanStore()
    older = json.loads(asyncio.run(create_plan("Học guitar", ["Mua giáo trình"], store=store)).output)
    decoy = json.loads(asyncio.run(create_plan("Nấu ăn", ["Cắt rau"], store=store)).output)
    newer = json.loads(asyncio.run(create_plan("Học tiếng Nhật", ["Mua giáo trình Nhật"], store=store)).output)
    listed = _plans(asyncio.run(get_plans("giáo trình", store=store)))
    assert [plan["id"] for plan in listed] == [newer["id"], older["id"]]
    assert decoy["id"] not in [plan["id"] for plan in listed]


def test_title_only_match_newer_than_goal_only_match_comes_first() -> None:
    store = MemoryPlanStore()
    goal_only = json.loads(asyncio.run(create_plan("Mua giáo trình Nhật", ["Hợp âm"], store=store)).output)
    decoy = json.loads(asyncio.run(create_plan("Nấu ăn", ["Cắt rau"], store=store)).output)
    title_only = json.loads(asyncio.run(create_plan("Học guitar", ["Đọc giáo trình"], store=store)).output)
    listed = _plans(asyncio.run(get_plans("giáo trình", store=store)))
    assert [plan["id"] for plan in listed] == [title_only["id"], goal_only["id"]]
    assert decoy["id"] not in [plan["id"] for plan in listed]


def test_keyword_with_no_match_is_empty_success() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học guitar", store=store))
    result = asyncio.run(get_plans("Nhật", store=store))
    assert result.success is True
    assert json.loads(result.output) == {"plans": []}


@pytest.mark.parametrize("keyword", [None, "", "   "])
def test_blank_keyword_matches_unfiltered_list(keyword: str | None) -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học guitar", ["một"], store=store))
    asyncio.run(create_plan("Học tiếng Nhật", ["hai"], store=store))
    assert _plans(asyncio.run(get_plans(keyword, store=store))) == _plans(asyncio.run(get_plans(store=store)))


def test_nfd_goal_matches_nfc_keyword() -> None:
    store = MemoryPlanStore()
    nfd_goal = unicodedata.normalize("NFD", "Học tiếng Nhật")
    asyncio.run(create_plan(nfd_goal, store=store))
    keyword = unicodedata.normalize("NFC", "tiếng")
    listed = _plans(asyncio.run(get_plans(keyword, store=store)))
    assert len(listed) == 1
    assert listed[0]["goal"] == unicodedata.normalize("NFC", "Học tiếng Nhật")


def test_keyword_inner_double_space_does_not_match() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", store=store))
    assert _plans(asyncio.run(get_plans("tiếng  Nhật", store=store))) == []


def test_two_plans_with_same_goal_both_match_keyword() -> None:
    store = MemoryPlanStore()
    first = json.loads(asyncio.run(create_plan("Học tiếng Nhật", ["một"], store=store)).output)
    second = json.loads(asyncio.run(create_plan("Học tiếng Nhật", ["hai"], store=store)).output)
    listed = _plans(asyncio.run(get_plans("Nhật", store=store)))
    assert [plan["id"] for plan in listed] == [second["id"], first["id"]]
    assert listed[0]["id"] != listed[1]["id"]


def _subtask(title: str, status: SubtaskStatus, note: str | None) -> Subtask:
    return Subtask(id=str(uuid.uuid4()), title=title, status=status, note=note)


def test_keyword_on_middle_done_subtask_returns_whole_plan() -> None:
    store = MemoryPlanStore()
    asyncio.run(
        store.add(
            "Học guitar",
            (
                _subtask("Mua vở", SubtaskStatus.PENDING, "vở mới"),
                _subtask("Học hiragana", SubtaskStatus.DONE, "xong bảng"),
                _subtask("Nghe hội thoại", SubtaskStatus.PENDING, None),
            ),
        )
    )
    result = asyncio.run(get_plans("hiragana", store=store))
    assert result.success is True
    plans = json.loads(result.output)["plans"]
    assert len(plans) == 1
    items = plans[0]["subtasks"]
    assert [item["title"] for item in items] == ["Mua vở", "Học hiragana", "Nghe hội thoại"]
    assert [(item["status"], item["note"]) for item in items] == [
        ("pending", "vở mới"),
        ("done", "xong bảng"),
        ("pending", None),
    ]


def test_keyword_on_skipped_title_returns_plan_still_skipped() -> None:
    store = MemoryPlanStore()
    asyncio.run(
        store.add(
            "Học guitar",
            (
                _subtask("Học katakana", SubtaskStatus.SKIPPED, "để sau"),
                _subtask("Nghe hội thoại", SubtaskStatus.PENDING, "mỗi ngày"),
            ),
        )
    )
    result = asyncio.run(get_plans("katakana", store=store))
    assert result.success is True
    plans = json.loads(result.output)["plans"]
    assert len(plans) == 1
    items = plans[0]["subtasks"]
    assert [(item["title"], item["status"], item["note"]) for item in items] == [
        ("Học katakana", "skipped", "để sau"),
        ("Nghe hội thoại", "pending", "mỗi ngày"),
    ]


def test_title_casefold_and_padding_match_when_goal_does_not() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học guitar", ["Học tiếng Nhật"], store=store))
    assert _plans(asyncio.run(get_plans("TIẾNG", store=store)))[0]["goal"] == "Học guitar"
    assert _plans(asyncio.run(get_plans("  Nhật  ", store=store)))[0]["goal"] == "Học guitar"


def test_tieng_without_diacritic_does_not_match_title() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học guitar", ["Học tiếng Nhật"], store=store))
    assert _plans(asyncio.run(get_plans("tieng", store=store))) == []


def test_title_inner_double_space_does_not_match() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học guitar", ["tiếng Nhật"], store=store))
    assert _plans(asyncio.run(get_plans("tiếng  Nhật", store=store))) == []


def test_nfd_title_matches_nfc_keyword() -> None:
    store = MemoryPlanStore()
    nfd_title = unicodedata.normalize("NFD", "Học tiếng Nhật")
    asyncio.run(store.add("Học guitar", (_subtask(nfd_title, SubtaskStatus.PENDING, None),)))
    keyword = unicodedata.normalize("NFC", "tiếng")
    result = asyncio.run(get_plans(keyword, store=store))
    assert result.success is True
    plans = json.loads(result.output)["plans"]
    assert len(plans) == 1
    assert plans[0]["subtasks"][0]["title"] == nfd_title
    assert plans[0]["subtasks"][0]["status"] == "pending"


def test_keyword_only_in_note_is_empty_success() -> None:
    store = MemoryPlanStore()
    asyncio.run(store.add("Học guitar", (_subtask("Hợp âm", SubtaskStatus.PENDING, "giáo trình"),)))
    result = asyncio.run(get_plans("giáo trình", store=store))
    assert result.success is True
    assert json.loads(result.output)["plans"] == []

