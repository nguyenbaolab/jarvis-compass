"""update_subtask đặt trạng thái một việc con, hoặc từ chối đúng câu đầu tiên."""

import asyncio

import pytest

from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.helpers import (
    ReplaceCounter,
    listed_plans,
    pending_or_done_plan,
    update_subtask_refusal,
    upper_changed,
)
from tools.plan_tools import create_plan, get_plan_detail, update_subtask


def test_created_open_and_list_share_pending_ids() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        ))
    )
    opened = pending_or_done_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert opened == created
    assert listed_plans(store) == [created]
    assert [item["title"] for item in created["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert [item["status"] for item in created["subtasks"]] == ["pending", "pending"]


def test_mark_done_matches_detail_then_pending_on_open_and_list() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        ))
    )
    first, second = created["subtasks"]
    updated = pending_or_done_plan(asyncio.run(update_subtask(created["id"], first["id"], "done", store=store)))
    opened = pending_or_done_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert updated == opened
    assert updated["id"] == created["id"]
    assert updated["goal"] == "Học tiếng Nhật"
    assert [item["id"] for item in updated["subtasks"]] == [first["id"], second["id"]]
    assert [item["title"] for item in updated["subtasks"]] == [
        "Học hiragana",
        "Luyện 10 phút mỗi ngày",
    ]
    assert [item["status"] for item in updated["subtasks"]] == ["done", "pending"]

    again = pending_or_done_plan(asyncio.run(update_subtask(created["id"], first["id"], "pending", store=store)))
    assert again["subtasks"][0]["status"] == "pending"
    assert again["subtasks"][0]["id"] == first["id"]
    opened_again = pending_or_done_plan(asyncio.run(get_plan_detail(created["id"], store=store)))
    assert opened_again["subtasks"][0]["status"] == "pending"
    listed = listed_plans(store)
    assert listed[0]["id"] == created["id"]
    assert listed[0]["subtasks"][0]["status"] == "pending"


def test_mark_done_again_stays_done() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    subtask_id = created["subtasks"][0]["id"]
    pending_or_done_plan(asyncio.run(update_subtask(created["id"], subtask_id, "done", store=store)))
    again = pending_or_done_plan(asyncio.run(update_subtask(created["id"], subtask_id, "done", store=store)))
    assert again["id"] == created["id"]
    assert again["subtasks"][0]["id"] == subtask_id
    assert again["subtasks"][0]["status"] == "done"
    assert again["subtasks"][0]["title"] == "Học hiragana"


def test_mark_pending_again_does_not_replace() -> None:
    store = ReplaceCounter()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    subtask_id = created["subtasks"][0]["id"]
    again = pending_or_done_plan(asyncio.run(update_subtask(created["id"], subtask_id, "pending", store=store)))
    assert again["id"] == created["id"]
    assert again["subtasks"][0]["status"] == "pending"
    assert again["subtasks"][0]["id"] == subtask_id
    assert store.replace_calls == 0


def test_same_title_updates_only_the_chosen_id() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Ôn bài", ["Ôn bài", "Ôn bài"], store=store)))
    first, second = created["subtasks"]
    updated = pending_or_done_plan(asyncio.run(update_subtask(created["id"], first["id"], "done", store=store)))
    assert updated["subtasks"][0]["id"] == first["id"]
    assert updated["subtasks"][0]["status"] == "done"
    assert updated["subtasks"][1]["id"] == second["id"]
    assert updated["subtasks"][1]["status"] == "pending"
    assert updated["subtasks"][0]["title"] == updated["subtasks"][1]["title"] == "Ôn bài"


def test_all_done_stays_in_unfiltered_list() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(
        asyncio.run(create_plan(
            "Học tiếng Nhật",
            ["Học hiragana", "Luyện 10 phút mỗi ngày"],
            store=store,
        ))
    )
    current = created
    for item in created["subtasks"]:
        current = pending_or_done_plan(asyncio.run(update_subtask(created["id"], item["id"], "done", store=store)))
    assert [item["status"] for item in current["subtasks"]] == ["done", "done"]
    assert [plan["id"] for plan in listed_plans(store)] == [created["id"]]


def test_padded_status_and_ids_match() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    subtask_id = created["subtasks"][0]["id"]
    updated = pending_or_done_plan(
        asyncio.run(update_subtask(
            f"  {created['id']}  ",
            f"  {subtask_id}  ",
            " done ",
            store=store,
        ))
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


def _mark_first_done(store: MemoryPlanStore, created: dict) -> None:
    updated = pending_or_done_plan(
        asyncio.run(update_subtask(created["id"], created["subtasks"][0]["id"], "done", store=store))
    )
    assert updated["subtasks"][0]["status"] == "done"


@pytest.mark.parametrize("plan_id", [None, "", "   "])
def test_blank_plan_id_wins(plan_id: str | None) -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert update_subtask_refusal(plan_id, None, "xong", store) == _BLANK_PLAN
    assert listed_plans(store) == before
    _mark_first_done(store, created)


@pytest.mark.parametrize("subtask_id", [None, "", "   "])
def test_blank_subtask_id_wins_before_lookup(subtask_id: str | None) -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert update_subtask_refusal("không-có-kế-hoạch", subtask_id, "xong", store) == _BLANK_SUBTASK
    assert listed_plans(store) == before
    _mark_first_done(store, created)


@pytest.mark.parametrize(
    "status",
    [None, "", "   ", "xong", "chưa xong", "Done", "PENDING"],
)
def test_bad_status_wins_before_lookup(status: str | None) -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert update_subtask_refusal("không-có-kế-hoạch", "một-việc", status, store) == _BAD_STATUS
    assert listed_plans(store) == before
    _mark_first_done(store, created)


def test_missing_plan_after_inputs_are_valid() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    missing = "00000000-0000-4000-8000-000000000000"
    assert missing != created["id"]
    before = listed_plans(store)
    assert update_subtask_refusal(missing, created["subtasks"][0]["id"], "done", store) == _MISSING_PLAN
    assert listed_plans(store) == before
    _mark_first_done(store, created)


def test_subtask_of_another_plan_is_rejected() -> None:
    store = MemoryPlanStore()
    plan_a = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    plan_b = pending_or_done_plan(asyncio.run(create_plan("Viết báo cáo", ["Soạn đề cương"], store=store)))
    before = listed_plans(store)
    assert (
        update_subtask_refusal(plan_a["id"], plan_b["subtasks"][0]["id"], "done", store) == _NOT_IN_PLAN
    )
    assert listed_plans(store) == before
    assert pending_or_done_plan(asyncio.run(get_plan_detail(plan_a["id"], store=store)))["subtasks"][0]["status"] == "pending"
    assert pending_or_done_plan(asyncio.run(get_plan_detail(plan_b["id"], store=store)))["subtasks"][0]["status"] == "pending"
    _mark_first_done(store, plan_a)
    assert pending_or_done_plan(asyncio.run(get_plan_detail(plan_b["id"], store=store)))["subtasks"][0]["status"] == "pending"


@pytest.mark.parametrize("subtask_id", ["Học hiragana", "1"])
def test_title_or_position_is_not_subtask_id(subtask_id: str) -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    assert created["subtasks"][0]["id"] != subtask_id
    before = listed_plans(store)
    assert update_subtask_refusal(created["id"], subtask_id, "done", store) == _NOT_IN_PLAN
    assert listed_plans(store) == before
    _mark_first_done(store, created)


def test_plan_without_subtasks_rejects_any_subtask_id() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Viết báo cáo", store=store)))
    other = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert update_subtask_refusal(created["id"], "một-việc", "done", store) == _NOT_IN_PLAN
    assert listed_plans(store) == before
    assert pending_or_done_plan(asyncio.run(get_plan_detail(created["id"], store=store)))["subtasks"] == []
    _mark_first_done(store, other)


def test_title_fragment_is_not_subtask_id() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert update_subtask_refusal(created["id"], "hiragana", "done", store) == _NOT_IN_PLAN
    assert listed_plans(store) == before
    _mark_first_done(store, created)


def test_uppercase_plan_id_is_missing() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert (
        update_subtask_refusal(upper_changed(created["id"]), created["subtasks"][0]["id"], "done", store)
        == _MISSING_PLAN
    )
    assert listed_plans(store) == before
    _mark_first_done(store, created)


def test_uppercase_subtask_id_is_not_in_plan() -> None:
    store = MemoryPlanStore()
    created = pending_or_done_plan(asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)))
    before = listed_plans(store)
    assert (
        update_subtask_refusal(created["id"], upper_changed(created["subtasks"][0]["id"]), "done", store)
        == _NOT_IN_PLAN
    )
    assert listed_plans(store) == before
    assert pending_or_done_plan(asyncio.run(get_plan_detail(created["id"], store=store)))["subtasks"][0]["status"] == "pending"
    _mark_first_done(store, created)
