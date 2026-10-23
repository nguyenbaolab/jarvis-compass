"""add_subtask thêm một việc con vào cuối, hoặc từ chối đúng câu đầu tiên."""

import json
import re
import unicodedata

import pytest

from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import add_subtask, create_plan, get_plan_detail, get_plans, update_subtask

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_BLANK_PLAN = "Danh tính kế hoạch chưa được đưa."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_BLANK_TITLE = "Việc con không được để trống."


def _plan(result: ToolResult) -> dict:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"id", "goal", "subtasks"}
    assert _UUID.fullmatch(data["id"])
    seen: set[str] = set()
    for item in data["subtasks"]:
        assert list(item) == ["id", "title", "status"]
        assert isinstance(item["title"], str)
        assert item["status"] in {"pending", "done"}
        assert _UUID.fullmatch(item["id"])
        assert item["id"] != data["id"]
        assert item["id"] not in seen
        seen.add(item["id"])
    return data


def _listed(store: MemoryPlanStore) -> list[dict]:
    result = get_plans(store=store)
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"plans"}
    return data["plans"]


def _open(plan_id: str, store: MemoryPlanStore) -> dict:
    return _plan(get_plan_detail(plan_id, store=store))


def test_add_appends_pending_and_matches_open_and_list() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    done = _plan(
        update_subtask(created["id"], created["subtasks"][1]["id"], "done", store=store)
    )
    added = _plan(add_subtask(created["id"], "Mua giáo trình", store=store))
    assert added["id"] == created["id"]
    assert added["goal"] == "Học tiếng Nhật"
    assert added["subtasks"][:2] == done["subtasks"]
    assert added["subtasks"][2]["title"] == "Mua giáo trình"
    assert added["subtasks"][2]["status"] == "pending"
    assert _open(created["id"], store) == added
    assert _listed(store) == [added]


def test_add_to_plan_with_no_subtasks() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Viết báo cáo", store=store))
    added = _plan(add_subtask(created["id"], "Soạn dàn ý", store=store))
    assert added["goal"] == "Viết báo cáo"
    assert len(added["subtasks"]) == 1
    assert added["subtasks"][0]["title"] == "Soạn dàn ý"
    assert added["subtasks"][0]["status"] == "pending"


def test_two_adds_keep_earlier_identity() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    first = _plan(add_subtask(created["id"], "Mua sách", store=store))
    second = _plan(add_subtask(created["id"], "Đọc chương 1", store=store))
    assert [item["title"] for item in second["subtasks"]] == [
        "Học hiragana",
        "Mua sách",
        "Đọc chương 1",
    ]
    assert second["subtasks"][1]["id"] == first["subtasks"][1]["id"]
    assert second["subtasks"][1]["status"] == "pending"


def test_title_strips_ends_and_keeps_inner_spaces() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["cũ"], store=store))
    padded = _plan(add_subtask(created["id"], "  Mua giáo trình  ", store=store))
    assert padded["subtasks"][1]["title"] == "Mua giáo trình"
    spaced = _plan(add_subtask(created["id"], "Học  hiragana", store=store))
    assert spaced["subtasks"][2]["title"] == "Học  hiragana"


def test_nfd_title_is_stored_and_returned_as_nfc() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", store=store))
    nfd_title = unicodedata.normalize("NFD", "Mua giáo trình")
    nfc_title = unicodedata.normalize("NFC", "Mua giáo trình")
    assert nfd_title != nfc_title
    added = _plan(add_subtask(created["id"], nfd_title, store=store))
    assert added["subtasks"][-1]["title"] == nfc_title
    assert _open(created["id"], store)["subtasks"][-1]["title"] == nfc_title


def test_comma_and_newline_stay_one_subtask() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", store=store))
    title = "Mua sách,\nđọc một chương"
    added = _plan(add_subtask(created["id"], title, store=store))
    assert len(added["subtasks"]) == 1
    assert added["subtasks"][0]["title"] == title


def test_duplicate_title_gets_its_own_id_at_the_end() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Ôn bài"], store=store))
    added = _plan(add_subtask(created["id"], "Ôn bài", store=store))
    assert [item["title"] for item in added["subtasks"]] == ["Ôn bài", "Ôn bài"]
    assert added["subtasks"][0]["id"] == created["subtasks"][0]["id"]
    assert added["subtasks"][1]["id"] != added["subtasks"][0]["id"]
    assert added["subtasks"][0]["status"] == "pending"


def test_list_order_stays_when_adding_to_middle_plan() -> None:
    store = MemoryPlanStore()
    plan_a = _plan(create_plan("Kế hoạch A", ["việc A"], store=store))
    plan_b = _plan(create_plan("Kế hoạch B", ["việc B"], store=store))
    plan_c = _plan(create_plan("Kế hoạch C", ["việc C"], store=store))
    marked = _plan(
        update_subtask(plan_b["id"], plan_b["subtasks"][0]["id"], "done", store=store)
    )
    added = _plan(add_subtask(plan_b["id"], "việc mới", store=store))
    listed = _listed(store)
    assert [item["id"] for item in listed] == [plan_c["id"], plan_b["id"], plan_a["id"]]
    assert listed[1] == added
    assert added["subtasks"][0] == marked["subtasks"][0]
    assert added["subtasks"][1]["status"] == "pending"


def test_padded_plan_id_hits_the_same_plan() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    added = _plan(add_subtask(f"  {created['id']}  ", "Mua giáo trình", store=store))
    assert added["id"] == created["id"]
    assert added["subtasks"][0] == created["subtasks"][0]


def test_keyword_matches_goal_not_new_title() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", store=store))
    added = _plan(add_subtask(created["id"], "Mua giáo trình", store=store))
    assert added["subtasks"][-1]["title"] == "Mua giáo trình"
    assert [item["title"] for item in added["subtasks"]] == ["Mua giáo trình"]
    title_only = get_plans("giáo trình", store=store)
    assert title_only.success is True
    assert json.loads(title_only.output) == {"plans": []}
    by_goal = json.loads(get_plans("Nhật", store=store).output)
    assert by_goal["plans"][0]["id"] == created["id"]


def _refusal(plan_id: str | None, title: str | None, store: MemoryPlanStore) -> str:
    with pytest.raises(ToolError) as caught:
        add_subtask(plan_id, title, store=store)
    return str(caught.value)


def _add_after(created: dict, store: MemoryPlanStore) -> None:
    added = _plan(add_subtask(created["id"], "Mua giáo trình", store=store))
    assert added["subtasks"][-1]["title"] == "Mua giáo trình"


@pytest.mark.parametrize("plan_id", [None, "", "   "])
def test_blank_plan_id_with_valid_title(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal(plan_id, "Mua giáo trình", store) == _BLANK_PLAN
    assert _listed(store) == before


@pytest.mark.parametrize("plan_id", [None, "", "   "])
def test_blank_plan_id_wins(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal(plan_id, None, store) == _BLANK_PLAN
    assert _listed(store) == before
    _add_after(created, store)


def test_missing_plan_after_title_is_valid() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    missing = "00000000-0000-4000-8000-000000000000"
    assert missing != created["id"]
    before = _listed(store)
    assert _refusal(missing, "Mua giáo trình", store) == _MISSING_PLAN
    assert _listed(store) == before
    _add_after(created, store)


@pytest.mark.parametrize("title", [None, "", "   "])
def test_blank_title_on_real_plan(title: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _open(created["id"], store)
    assert _refusal(created["id"], title, store) == _BLANK_TITLE
    assert _open(created["id"], store) == before
    assert len(before["subtasks"]) == 1
    _add_after(created, store)


def test_blank_title_wins_before_lookup() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal("không-có-kế-hoạch", "   ", store) == _BLANK_TITLE
    assert _listed(store) == before
    _add_after(created, store)


def _upper(value: str) -> str:
    changed = value.upper()
    assert changed != value
    return changed


def test_goal_or_uppercase_id_is_missing() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal("Học tiếng Nhật", "Mua giáo trình", store) == _MISSING_PLAN
    assert _refusal(_upper(created["id"]), "Mua giáo trình", store) == _MISSING_PLAN
    assert _listed(store) == before
    _add_after(created, store)


def test_create_plan_rejects_none_title() -> None:
    store = MemoryPlanStore()
    create_plan("Đã có", ["cũ"], store=store)
    with pytest.raises(ToolError) as caught:
        create_plan("Mới", [None], store=store)  # type: ignore[list-item]
    assert str(caught.value) == _BLANK_TITLE
    stored = store.list_newest_first()
    assert len(stored) == 1
    assert stored[0].goal == "Đã có"
