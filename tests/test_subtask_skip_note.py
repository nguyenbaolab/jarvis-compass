"""Trạng thái skipped và một ghi chú cho mỗi việc con."""

import json
import re
import unicodedata

import pytest

from core.plans import Plan
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import (
    add_subtask,
    create_plan,
    get_plan_detail,
    get_plans,
    set_subtask_note,
    update_subtask,
)

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_BAD_STATUS = "Trạng thái việc con chỉ nhận pending, done hoặc skipped."
_BLANK_PLAN = "Danh tính kế hoạch chưa được đưa."
_BLANK_SUBTASK = "Danh tính việc con chưa được đưa."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_NOT_IN_PLAN = "Kế hoạch này không có việc con với danh tính này."


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
        assert item["status"] in {"pending", "done", "skipped"}
        assert item["note"] is None or isinstance(item["note"], str)
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


def _refusal(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    store: MemoryPlanStore,
) -> str:
    with pytest.raises(ToolError) as caught:
        update_subtask(plan_id, subtask_id, status, store=store)
    return str(caught.value)


def test_skip_cycle_keeps_identity_and_null_notes() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    plan_id = created["id"]
    goal = created["goal"]
    ids = [item["id"] for item in created["subtasks"]]
    titles = [item["title"] for item in created["subtasks"]]
    current = created
    for status in ("skipped", "done", "pending", "skipped"):
        current = _plan(update_subtask(plan_id, ids[0], status, store=store))
        assert current["id"] == plan_id
        assert current["goal"] == goal
        assert [item["id"] for item in current["subtasks"]] == ids
        assert [item["title"] for item in current["subtasks"]] == titles
        assert current["subtasks"][0]["status"] == status
        assert current["subtasks"][1]["status"] == "pending"
        assert current["subtasks"][0]["note"] is None
        assert current["subtasks"][1]["note"] is None
        opened = _open(plan_id, store)
        listed = _listed(store)
        assert opened["subtasks"][0]["status"] == status
        assert listed[0]["id"] == plan_id
        assert listed[0]["subtasks"][0]["status"] == status
    assert current["subtasks"][0]["status"] == "skipped"


def test_all_skipped_stays_listed_and_open() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    for item in created["subtasks"]:
        _plan(update_subtask(created["id"], item["id"], "skipped", store=store))
    listed = _listed(store)
    assert listed[0]["id"] == created["id"]
    assert listed[0]["goal"] == created["goal"]
    opened = _open(created["id"], store)
    assert opened["id"] == created["id"]
    assert opened["goal"] == created["goal"]
    assert [item["status"] for item in opened["subtasks"]] == ["skipped", "skipped"]


def test_mixed_done_and_skipped_stays_listed_and_open() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    _plan(update_subtask(created["id"], created["subtasks"][0]["id"], "done", store=store))
    _plan(update_subtask(created["id"], created["subtasks"][1]["id"], "skipped", store=store))
    listed = _listed(store)
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    opened = _open(created["id"], store)
    assert opened["id"] == created["id"]
    assert [item["status"] for item in opened["subtasks"]] == ["done", "skipped"]


def test_padded_skipped_is_accepted() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    updated = _plan(
        update_subtask(created["id"], created["subtasks"][0]["id"], " skipped ", store=store)
    )
    assert updated["subtasks"][0]["status"] == "skipped"


@pytest.mark.parametrize("status", ["Skipped", "SKIPPED", "bỏ qua"])
def test_bad_status_names_three_codes_before_lookup(status: str) -> None:
    store = MemoryPlanStore()
    _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _refusal("không-có-kế-hoạch", "một-việc", status, store) == _BAD_STATUS
    assert _listed(store) == before


def test_same_skipped_does_not_replace() -> None:
    store = _ReplaceCounter()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    _plan(update_subtask(created["id"], created["subtasks"][0]["id"], "skipped", store=store))
    calls = store.replace_calls
    again = _plan(
        update_subtask(created["id"], created["subtasks"][0]["id"], "skipped", store=store)
    )
    assert again["subtasks"][0]["status"] == "skipped"
    assert store.replace_calls == calls


def test_new_subtask_note_is_null_on_list_and_open() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    assert created["subtasks"][0]["note"] is None
    listed = _listed(store)
    opened = _open(created["id"], store)
    assert listed[0]["subtasks"][0]["note"] is None
    assert opened["subtasks"][0]["note"] is None


def test_added_subtask_has_null_note_and_keeps_key_order() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", store=store))
    added = _plan(add_subtask(created["id"], "Mua giáo trình", store=store))
    assert list(added["subtasks"][0]) == ["id", "title", "status", "note"]
    assert added["subtasks"][0]["note"] is None
    assert added["subtasks"][0]["status"] == "pending"


def test_note_on_one_of_two_subtasks_keeps_the_other() -> None:
    store = MemoryPlanStore()
    created = _plan(
        create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        )
    )
    first = created["subtasks"][0]
    second = created["subtasks"][1]
    updated = _plan(set_subtask_note(created["id"], first["id"], "Đợi giáo trình", store=store))
    assert updated["id"] == created["id"]
    assert updated["goal"] == created["goal"]
    assert [item["id"] for item in updated["subtasks"]] == [first["id"], second["id"]]
    assert updated["subtasks"][0]["id"] == first["id"]
    assert updated["subtasks"][0]["title"] == first["title"]
    assert updated["subtasks"][0]["status"] == first["status"]
    assert updated["subtasks"][0]["note"] == "Đợi giáo trình"
    assert updated["subtasks"][1]["id"] == second["id"]
    assert updated["subtasks"][1]["title"] == second["title"]
    assert updated["subtasks"][1]["status"] == second["status"]
    assert updated["subtasks"][1]["note"] == second["note"]


def test_note_survives_status_change_and_status_survives_note() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    done = _plan(update_subtask(created["id"], subtask_id, "done", store=store))
    assert done["subtasks"][0]["status"] == "done"
    noted = _plan(set_subtask_note(created["id"], subtask_id, "Đợi giáo trình", store=store))
    assert noted["subtasks"][0]["status"] == "done"
    assert noted["subtasks"][0]["note"] == "Đợi giáo trình"
    skipped = _plan(update_subtask(created["id"], subtask_id, "skipped", store=store))
    assert skipped["subtasks"][0]["status"] == "skipped"
    assert skipped["subtasks"][0]["note"] == "Đợi giáo trình"
    opened = _open(created["id"], store)
    assert opened["subtasks"][0]["note"] == "Đợi giáo trình"
    assert _listed(store)[0]["subtasks"][0]["note"] == "Đợi giáo trình"


def test_new_note_overwrites_the_old_one() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    _plan(set_subtask_note(created["id"], subtask_id, "Đợi giáo trình", store=store))
    updated = _plan(set_subtask_note(created["id"], subtask_id, "Học sau", store=store))
    assert updated["subtasks"][0]["note"] == "Học sau"


def test_note_strips_ends() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    updated = _plan(
        set_subtask_note(created["id"], created["subtasks"][0]["id"], "  Đợi giáo trình  ", store=store)
    )
    assert updated["subtasks"][0]["note"] == "Đợi giáo trình"


def test_nfd_note_is_stored_as_nfc() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    nfd_note = unicodedata.normalize("NFD", "Mua giáo trình")
    nfc_note = unicodedata.normalize("NFC", "Mua giáo trình")
    assert nfd_note != nfc_note
    updated = _plan(set_subtask_note(created["id"], created["subtasks"][0]["id"], nfd_note, store=store))
    assert updated["subtasks"][0]["note"] == nfc_note
    assert _open(created["id"], store)["subtasks"][0]["note"] == nfc_note


def test_note_keeps_comma_newline_and_inner_spaces() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    raw = "Đợi,  giáo\ntrình"
    updated = _plan(set_subtask_note(created["id"], created["subtasks"][0]["id"], raw, store=store))
    assert updated["subtasks"][0]["note"] == raw


@pytest.mark.parametrize("note", [None, "", "   "])
def test_clearing_a_note_keeps_status(note: str | None) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    _plan(update_subtask(created["id"], subtask_id, "skipped", store=store))
    _plan(set_subtask_note(created["id"], subtask_id, "Đợi giáo trình", store=store))
    cleared = _plan(set_subtask_note(created["id"], subtask_id, note, store=store))
    assert cleared["subtasks"][0]["note"] is None
    assert cleared["subtasks"][0]["status"] == "skipped"


def test_long_note_is_stored_in_full() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    note = "Đợi " + ("a" * 5000)
    updated = _plan(set_subtask_note(created["id"], created["subtasks"][0]["id"], note, store=store))
    assert updated["subtasks"][0]["note"] == note
    assert _open(created["id"], store)["subtasks"][0]["note"] == note


def test_add_subtask_keeps_existing_note() -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    _plan(update_subtask(created["id"], subtask_id, "skipped", store=store))
    _plan(set_subtask_note(created["id"], subtask_id, "Đợi giáo trình", store=store))
    added = _plan(add_subtask(created["id"], "Mua giáo trình", store=store))
    assert added["subtasks"][0]["id"] == subtask_id
    assert added["subtasks"][0]["note"] == "Đợi giáo trình"
    assert added["subtasks"][0]["status"] == "skipped"
    assert added["subtasks"][1]["note"] is None
    assert added["subtasks"][1]["status"] == "pending"


def test_same_note_does_not_replace() -> None:
    store = _ReplaceCounter()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    subtask_id = created["subtasks"][0]["id"]
    _plan(set_subtask_note(created["id"], subtask_id, "Đợi giáo trình", store=store))
    calls = store.replace_calls
    again = _plan(set_subtask_note(created["id"], subtask_id, "  Đợi giáo trình  ", store=store))
    assert again["subtasks"][0]["note"] == "Đợi giáo trình"
    assert store.replace_calls == calls


@pytest.mark.parametrize("note", [None, "", "   "])
def test_clearing_absent_note_does_not_replace(note: str | None) -> None:
    store = _ReplaceCounter()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    calls = store.replace_calls
    again = _plan(set_subtask_note(created["id"], created["subtasks"][0]["id"], note, store=store))
    assert again["subtasks"][0]["note"] is None
    assert store.replace_calls == calls


def _note_refusal(
    plan_id: str | None,
    subtask_id: str | None,
    note: str | None,
    store: MemoryPlanStore,
) -> str:
    with pytest.raises(ToolError) as caught:
        set_subtask_note(plan_id, subtask_id, note, store=store)
    return str(caught.value)


@pytest.mark.parametrize("plan_id", [None, "", "   "])
def test_blank_plan_id_wins_for_note(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _note_refusal(plan_id, None, None, store) == _BLANK_PLAN
    assert _listed(store) == before


@pytest.mark.parametrize("subtask_id", [None, "", "   "])
def test_blank_subtask_id_wins_before_note_lookup(subtask_id: str | None) -> None:
    store = MemoryPlanStore()
    _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    before = _listed(store)
    assert _note_refusal("không-có-kế-hoạch", subtask_id, "Đợi giáo trình", store) == _BLANK_SUBTASK
    assert _listed(store) == before


@pytest.mark.parametrize("note", ["Đợi giáo trình", "   "])
def test_missing_plan_after_note_inputs_are_valid(note: str) -> None:
    store = MemoryPlanStore()
    created = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    missing = "00000000-0000-4000-8000-000000000000"
    assert missing != created["id"]
    before = _listed(store)
    assert _note_refusal(missing, created["subtasks"][0]["id"], note, store) == _MISSING_PLAN
    assert _listed(store) == before
    placed = _plan(
        set_subtask_note(created["id"], created["subtasks"][0]["id"], "Đợi giáo trình", store=store)
    )
    assert placed["subtasks"][0]["note"] == "Đợi giáo trình"


def test_subtask_of_another_plan_rejects_note() -> None:
    store = MemoryPlanStore()
    plan_a = _plan(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    plan_b = _plan(create_plan("Viết báo cáo", ["Soạn đề cương"], store=store))
    before = _listed(store)
    assert (
        _note_refusal(plan_a["id"], plan_b["subtasks"][0]["id"], "Đợi giáo trình", store)
        == _NOT_IN_PLAN
    )
    assert _listed(store) == before
    placed = _plan(set_subtask_note(plan_a["id"], plan_a["subtasks"][0]["id"], "Học sau", store=store))
    assert placed["subtasks"][0]["note"] == "Học sau"
    assert _open(plan_b["id"], store)["subtasks"][0]["note"] is None
