"""update_subtask đặt trạng thái một việc con, hoặc từ chối đúng câu đầu tiên."""

import json
import re

import pytest

from core.plans import Plan
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import create_plan, get_plan_detail, get_plans, update_subtask

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class _ReplaceCounter(MemoryPlanStore):
    """Đếm lần replace trên đúng instance này."""

    def __init__(self) -> None:
        super().__init__()
        self.replace_calls = 0

    def replace(self, plan: Plan) -> None:
        self.replace_calls += 1
        super().replace(plan)


def _plan(result: ToolResult) -> dict:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"id", "goal", "subtasks"}
    assert _UUID.fullmatch(data["id"])
    seen: set[str] = set()
    for item in data["subtasks"]:
        assert list(item) == ["id", "title", "status", "note"]
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


def test_created_open_and_list_share_pending_ids() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    opened = _plan(get_plan_detail(created["id"], store=store))
    assert opened == created
    assert _listed(store) == [created]
    assert [item["title"] for item in created["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert [item["status"] for item in created["subtasks"]] == ["pending", "pending"]


def test_mark_done_matches_detail_then_pending_on_open_and_list() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    first, second = created["subtasks"]
    updated = _plan(update_subtask(created["id"], first["id"], "done", store=store))
    opened = _plan(get_plan_detail(created["id"], store=store))
    assert updated == opened
    assert updated["id"] == created["id"]
    assert updated["goal"] == "Học tiếng Nhật"
    assert [item["id"] for item in updated["subtasks"]] == [first["id"], second["id"]]
    assert [item["title"] for item in updated["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert [item["status"] for item in updated["subtasks"]] == ["done", "pending"]

    again = _plan(update_subtask(created["id"], first["id"], "pending", store=store))
    assert again["subtasks"][0]["status"] == "pending"
    assert again["subtasks"][0]["id"] == first["id"]
    opened_again = _plan(get_plan_detail(created["id"], store=store))
    assert opened_again["subtasks"][0]["status"] == "pending"
    listed = _listed(store)
    assert listed[0]["id"] == created["id"]
    assert listed[0]["subtasks"][0]["status"] == "pending"


def test_mark_done_again_stays_done() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    _plan(update_subtask(created["id"], subtask_id, "done", store=store))
    again = _plan(update_subtask(created["id"], subtask_id, "done", store=store))
    assert again["id"] == created["id"]
    assert again["subtasks"][0]["id"] == subtask_id
    assert again["subtasks"][0]["status"] == "done"
    assert again["subtasks"][0]["title"] == "Học hiragana"


def test_mark_pending_again_does_not_replace() -> None:
    store = _ReplaceCounter()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    again = _plan(update_subtask(created["id"], subtask_id, "pending", store=store))
    assert again["id"] == created["id"]
    assert again["subtasks"][0]["status"] == "pending"
    assert again["subtasks"][0]["id"] == subtask_id
    assert store.replace_calls == 0


def test_same_title_updates_only_the_chosen_id() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Ôn bài", ["Ôn bài", "Ôn bài"], store=store))
    first, second = created["subtasks"]
    updated = _plan(update_subtask(created["id"], first["id"], "done", store=store))
    assert updated["subtasks"][0]["id"] == first["id"]
    assert updated["subtasks"][0]["status"] == "done"
    assert updated["subtasks"][1]["id"] == second["id"]
    assert updated["subtasks"][1]["status"] == "pending"
    assert updated["subtasks"][0]["title"] == updated["subtasks"][1]["title"] == "Ôn bài"


def test_all_done_stays_in_unfiltered_list() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    current = created
    for item in created["subtasks"]:
        current = _plan(update_subtask(created["id"], item["id"], "done", store=store))
    assert [item["status"] for item in current["subtasks"]] == ["done", "done"]
    assert [plan["id"] for plan in _listed(store)] == [created["id"]]


def test_padded_status_and_ids_match() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    updated = _plan(
        update_subtask(
            f"  {created['id']}  ",
            f"  {subtask_id}  ",
            " done ",
            store=store,
        )
    )
    assert updated["id"] == created["id"]
    assert updated["subtasks"][0]["id"] == subtask_id
    assert updated["subtasks"][0]["status"] == "done"
    assert updated["subtasks"][0]["title"] == "Học hiragana"


_BLANK_PLAN = "Danh tính kế hoạch chưa được đưa."
_BLANK_SUBTASK = "Danh tính việc con chưa được đưa."
_BAD_STATUS = "Trạng thái việc con chỉ nhận pending, done hoặc skipped."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_NOT_IN_PLAN = "Kế hoạch này không có việc con với danh tính này."


def _refusal(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    store: MemoryPlanStore,
) -> str:
    with pytest.raises(ToolError) as caught:
        update_subtask(plan_id, subtask_id, status, store=store)
    return str(caught.value)


def _upper(value: str) -> str:
    changed = value.upper()
    assert changed != value
    return changed


def _mark_first_done(store: MemoryPlanStore, created: dict) -> None:
    updated = _plan(
        update_subtask(created["id"], created["subtasks"][0]["id"], "done", store=store)
    )
    assert updated["subtasks"][0]["status"] == "done"


@pytest.mark.parametrize("plan_id", [None, "", "   "])
def test_blank_plan_id_wins(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal(plan_id, None, "xong", store) == _BLANK_PLAN
    assert _listed(store) == before
    _mark_first_done(store, created)


@pytest.mark.parametrize("subtask_id", [None, "", "   "])
def test_blank_subtask_id_wins_before_lookup(subtask_id: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal("không-có-kế-hoạch", subtask_id, "xong", store) == _BLANK_SUBTASK
    assert _listed(store) == before
    _mark_first_done(store, created)


@pytest.mark.parametrize(
    "status",
    [None, "", "   ", "xong", "chưa xong", "Done", "PENDING"],
)
def test_bad_status_wins_before_lookup(status: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal("không-có-kế-hoạch", "một-việc", status, store) == _BAD_STATUS
    assert _listed(store) == before
    _mark_first_done(store, created)


def test_missing_plan_after_inputs_are_valid() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    missing = "00000000-0000-4000-8000-000000000000"
    assert missing != created["id"]
    before = _listed(store)
    assert _refusal(missing, created["subtasks"][0]["id"], "done", store) == _MISSING_PLAN
    assert _listed(store) == before
    _mark_first_done(store, created)


def test_subtask_of_another_plan_is_rejected() -> None:
    store = MemoryPlanStore()
    plan_a = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    plan_b = _plan(create_plan("Viết báo cáo", ["Soạn đề cương"], store=store))
    before = _listed(store)
    assert (
        _refusal(plan_a["id"], plan_b["subtasks"][0]["id"], "done", store) == _NOT_IN_PLAN
    )
    assert _listed(store) == before
    assert _plan(get_plan_detail(plan_a["id"], store=store))["subtasks"][0]["status"] == "pending"
    assert _plan(get_plan_detail(plan_b["id"], store=store))["subtasks"][0]["status"] == "pending"
    _mark_first_done(store, plan_a)
    assert _plan(get_plan_detail(plan_b["id"], store=store))["subtasks"][0]["status"] == "pending"


@pytest.mark.parametrize("subtask_id", ["Học hiragana", "1"])
def test_title_or_position_is_not_subtask_id(subtask_id: str) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    assert created["subtasks"][0]["id"] != subtask_id
    before = _listed(store)
    assert _refusal(created["id"], subtask_id, "done", store) == _NOT_IN_PLAN
    assert _listed(store) == before
    _mark_first_done(store, created)


def test_plan_without_subtasks_rejects_any_subtask_id() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Viết báo cáo", store=store))
    other = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal(created["id"], "một-việc", "done", store) == _NOT_IN_PLAN
    assert _listed(store) == before
    assert _plan(get_plan_detail(created["id"], store=store))["subtasks"] == []
    _mark_first_done(store, other)


def test_title_fragment_is_not_subtask_id() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal(created["id"], "hiragana", "done", store) == _NOT_IN_PLAN
    assert _listed(store) == before
    _mark_first_done(store, created)


def test_uppercase_plan_id_is_missing() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert (
        _refusal(_upper(created["id"]), created["subtasks"][0]["id"], "done", store)
        == _MISSING_PLAN
    )
    assert _listed(store) == before
    _mark_first_done(store, created)


def test_uppercase_subtask_id_is_not_in_plan() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert (
        _refusal(created["id"], _upper(created["subtasks"][0]["id"]), "done", store)
        == _NOT_IN_PLAN
    )
    assert _listed(store) == before
    assert _plan(get_plan_detail(created["id"], store=store))["subtasks"][0]["status"] == "pending"
    _mark_first_done(store, created)
