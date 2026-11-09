"""Test kho Supabase: host, ghi chú NULL, và hai mốc."""

import asyncio
import json
import uuid
from dataclasses import replace

import pytest

from core.plans import Plan, PlanConflictError, Subtask, SubtaskStatus
from config.settings import SettingsError
from db.plan_store import SupabasePlanStore
from tests.supabase_plan_db import prepare_local_source, read_subtask_note

_LOCAL_ONLY = "Test kho chỉ chạy trên kho local."


def test_remote_host_fails_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """prepare_local_source từ chối host xa, [::1], và URL không có host, trước factory."""

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("factory bị gọi")

    monkeypatch.setattr("tests.supabase_plan_db.postgrest_client", forbidden)
    monkeypatch.setenv("JARVIS_TEST_SUPABASE_KEY", "khoa-gia")
    for url in ("https://example.supabase.co", "http://[::1]:54321", "http://"):
        monkeypatch.setenv("JARVIS_TEST_SUPABASE_URL", url)
        with pytest.raises(RuntimeError) as caught:
            asyncio.run(prepare_local_source())
        assert str(caught.value) == _LOCAL_ONLY


def test_store_requires_both_settings_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dựng store thiếu khóa thì đúng câu FR-018, và không gọi mạng."""

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("factory bị gọi")

    monkeypatch.setattr("db.plan_store.postgrest_client", forbidden)
    cases = (
        ({}, "Thiếu SUPABASE_URL và SUPABASE_KEY."),
        ({"SUPABASE_KEY": "khoa-gia"}, "Thiếu SUPABASE_URL."),
        ({"SUPABASE_URL": "http://127.0.0.1:54321"}, "Thiếu SUPABASE_KEY."),
        ({"SUPABASE_URL": "", "SUPABASE_KEY": "khoa-gia"}, "Thiếu SUPABASE_URL."),
        ({"SUPABASE_URL": "http://127.0.0.1:54321", "SUPABASE_KEY": ""}, "Thiếu SUPABASE_KEY."),
    )
    for source, sentence in cases:
        with pytest.raises(SettingsError) as caught:
            SupabasePlanStore(source)
        message = str(caught.value)
        assert message == sentence
        assert "khoa-gia" not in message
        assert "127.0.0.1" not in message


def test_cleared_note_column_is_null() -> None:
    """Miền là None và cột SQL note là NULL."""

    asyncio.run(_cleared_note_column_is_null())


async def _cleared_note_column_is_null() -> None:
    source = await prepare_local_source()
    store = SupabasePlanStore(source)
    subtask = Subtask(
        id=str(uuid.uuid4()),
        title="Có ghi chú",
        status=SubtaskStatus.PENDING,
        note="Đợi giáo trình",
    )
    plan = await store.add("Ghi chú", (subtask,))
    cleared = replace(plan.subtasks[0], note=None)
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(cleared,),
            created_order=plan.created_order,
            version=plan.version,
        )
    )
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.subtasks[0].note is None
    raw = await read_subtask_note(source["SUPABASE_URL"], source["SUPABASE_KEY"], subtask.id)
    assert raw is None


def test_dropped_subtask_keeps_created_at_of_the_rest() -> None:
    """Việc còn sau replace bớt việc giữ created_at. Việc bỏ không còn dòng."""

    asyncio.run(_dropped_subtask_keeps_created_at_of_the_rest())


async def _dropped_subtask_keeps_created_at_of_the_rest() -> None:
    from tests.supabase_plan_db import read_subtask_clocks

    source = await prepare_local_source()
    store = SupabasePlanStore(source)
    kept = Subtask(id=str(uuid.uuid4()), title="Còn lại", status=SubtaskStatus.PENDING, note=None)
    dropped = Subtask(id=str(uuid.uuid4()), title="Bỏ đi", status=SubtaskStatus.PENDING, note=None)
    plan = await store.add("Bớt việc", (kept, dropped))
    created_at, _status_changed_at = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], kept.id
    )
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
    again, _again_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], kept.id
    )
    assert again == created_at
    with pytest.raises(AssertionError):
        await read_subtask_clocks(source["SUPABASE_URL"], source["SUPABASE_KEY"], dropped.id)


def test_clocks_follow_status_and_stay_out_of_tools() -> None:
    """Hai mốc đổi đúng luật và không có trong JSON của tool."""

    asyncio.run(_clocks_follow_status_and_stay_out_of_tools())


async def _clocks_follow_status_and_stay_out_of_tools() -> None:
    from tools.plan_tools import (
        add_subtask,
        create_plan,
        get_plan_detail,
        get_plans,
        set_subtask_note,
        update_subtask,
    )
    from tests.supabase_plan_db import read_subtask_clocks

    source = await prepare_local_source()
    store = SupabasePlanStore(source)
    first = Subtask(id=str(uuid.uuid4()), title="Việc một", status=SubtaskStatus.PENDING, note=None)
    plan = await store.add("Mốc", (first,))
    created_at, status_changed_at = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], first.id
    )
    assert created_at == status_changed_at
    assert created_at not in (None, "")

    renamed = replace(plan.subtasks[0], title="Việc một đã sửa", note="giữ trạng thái")
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(renamed,),
            created_order=plan.created_order,
            version=plan.version,
        )
    )
    same_created, same_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], first.id
    )
    assert same_created == created_at
    assert same_status == status_changed_at

    done = replace(renamed, status=SubtaskStatus.DONE)
    # Mỗi replace thành công tăng version 1.
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(done,),
            created_order=plan.created_order,
            version=plan.version + 1,
        )
    )
    kept_created, moved_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], first.id
    )
    assert kept_created == created_at
    assert moved_status != status_changed_at

    extra = Subtask(id=str(uuid.uuid4()), title="Việc hai", status=SubtaskStatus.PENDING, note=None)
    await store.replace(
        Plan(
            id=plan.id,
            goal=plan.goal,
            subtasks=(done, extra),
            created_order=plan.created_order,
            version=plan.version + 2,
        )
    )
    old_created, old_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], first.id
    )
    new_created, new_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], extra.id
    )
    assert old_created == created_at
    assert old_status == moved_status
    assert new_created == new_status
    assert new_created != created_at

    created = await create_plan("Tool", ["Việc tool"], store=store)
    assert created.success is True
    body = created.output
    assert "created_at" not in body
    assert "status_changed_at" not in body
    data = json.loads(body)
    plan_id = data["id"]
    subtask_id = data["subtasks"][0]["id"]
    results = (
        await get_plans(store=store),
        await get_plan_detail(plan_id, store=store),
        await update_subtask(plan_id, subtask_id, "done", store=store),
        await add_subtask(plan_id, "Việc thêm", store=store),
        await set_subtask_note(plan_id, subtask_id, "ghi chú", store=store),
    )
    for result in results:
        assert result.success is True
        assert "created_at" not in result.output
        assert "status_changed_at" not in result.output


def test_concurrent_replace_keeps_exactly_one() -> None:
    """Hai replace cùng version đã đọc: đúng một lần thành công."""

    asyncio.run(_concurrent_replace_keeps_exactly_one())


async def _concurrent_replace_keeps_exactly_one() -> None:
    source = await prepare_local_source()
    store = SupabasePlanStore(source)
    original = Subtask(id=str(uuid.uuid4()), title="Gốc", status=SubtaskStatus.PENDING, note=None)
    plan = await store.add("Cùng lúc", (original,))
    read = await store.get(plan.id)
    assert read is not None
    left = Subtask(id=str(uuid.uuid4()), title="Trái", status=SubtaskStatus.PENDING, note=None)
    right = Subtask(id=str(uuid.uuid4()), title="Phải", status=SubtaskStatus.PENDING, note=None)
    first = Plan(
        id=read.id,
        goal="Bản trái",
        subtasks=(left,),
        created_order=read.created_order,
        version=read.version,
    )
    second = Plan(
        id=read.id,
        goal="Bản phải",
        subtasks=(right,),
        created_order=read.created_order,
        version=read.version,
    )
    outcomes = await asyncio.gather(store.replace(first), store.replace(second), return_exceptions=True)
    successes = [item for item in outcomes if item is None]
    conflicts = [item for item in outcomes if isinstance(item, PlanConflictError)]
    assert len(successes) == 1
    assert len(conflicts) == 1
    opened = await store.get(plan.id)
    assert opened is not None
    assert opened.goal in {"Bản trái", "Bản phải"}
    assert opened.version == read.version + 1
    assert [item.title for item in opened.subtasks] == (
        ["Trái"] if opened.goal == "Bản trái" else ["Phải"]
    )


def _task(subtask_id: str, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": subtask_id,
        "title": "Việc",
        "status": "pending",
        "note": "ghi",
    }
    body.update(extra)
    return body


async def _rpc(source: dict[str, str], name: str, args: dict[str, object]) -> object:
    from db.client import postgrest_client

    async with postgrest_client(source["SUPABASE_URL"], source["SUPABASE_KEY"]) as client:
        response = await client.rpc(name, args).execute()
    return response.data


async def _value(source: dict[str, str], table: str, row_id: str, column: str) -> object:
    from db.client import postgrest_client

    async with postgrest_client(source["SUPABASE_URL"], source["SUPABASE_KEY"]) as client:
        response = await (
            client.from_(table).select(column).eq("id", row_id).maybe_single().execute()
        )
    if response is None or not isinstance(response.data, dict):
        raise AssertionError("không đọc được dòng")
    return response.data.get(column)


async def _seed(source: dict[str, str], task: dict[str, object], priority: str | None) -> str:
    data = await _rpc(
        source,
        "add_plan",
        {"goal": "Mục tiêu", "subtasks": [task], "priority": priority},
    )
    plan_id = data["id"] if isinstance(data, dict) else data[0]["id"]
    if not isinstance(plan_id, str):
        raise AssertionError("add_plan không trả id")
    return plan_id


def test_add_plan_two_args_is_not_ambiguous() -> None:
    asyncio.run(_add_plan_two_args_is_not_ambiguous())


async def _add_plan_two_args_is_not_ambiguous() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    await _rpc(
        source,
        "add_plan",
        {"goal": "Hai tham số", "subtasks": [_task(subtask_id)]},
    )
    assert await _value(source, "subtasks", subtask_id, "title") == "Việc"


def test_replace_plan_four_args_runs() -> None:
    asyncio.run(_replace_plan_four_args_runs())


async def _replace_plan_four_args_runs() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id), None)
    renamed = _task(subtask_id)
    renamed["title"] = "Đã sửa"
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [renamed],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "title") == "Đã sửa"


def test_missing_scheduled_on_keeps_stored_date() -> None:
    asyncio.run(_missing_scheduled_on_keeps_stored_date())


async def _missing_scheduled_on_keeps_stored_date() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id, scheduled_on="2026-11-06"), None)
    kept = _task(subtask_id, effort="S")
    kept["title"] = "Đã sửa"
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [kept],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "scheduled_on") == "2026-11-06"


def test_missing_effort_keeps_stored_effort() -> None:
    asyncio.run(_missing_effort_keeps_stored_effort())


async def _missing_effort_keeps_stored_effort() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id, effort="M"), None)
    kept = _task(subtask_id, scheduled_on="2026-11-06")
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [kept],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "effort") == "M"


def test_missing_plan_fields_keeps_priority() -> None:
    asyncio.run(_missing_plan_fields_keeps_priority())


async def _missing_plan_fields_keeps_priority() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id), "high")
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu mới",
            "subtasks": [_task(subtask_id)],
            "expected_version": 0,
        },
    )
    assert await _value(source, "plans", plan_id, "priority") == "high"


def test_json_null_clears_scheduled_on() -> None:
    asyncio.run(_json_null_clears_scheduled_on())


async def _json_null_clears_scheduled_on() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id, scheduled_on="2026-11-06"), None)
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [_task(subtask_id, scheduled_on=None)],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "scheduled_on") is None


def test_json_null_clears_effort() -> None:
    asyncio.run(_json_null_clears_effort())


async def _json_null_clears_effort() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id, effort="L"), None)
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [_task(subtask_id, effort=None)],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "effort") is None


def test_json_null_clears_priority() -> None:
    asyncio.run(_json_null_clears_priority())


async def _json_null_clears_priority() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id), "low")
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [_task(subtask_id)],
            "expected_version": 0,
            "plan_fields": {"priority": None},
        },
    )
    assert await _value(source, "plans", plan_id, "priority") is None


def test_missing_note_becomes_null() -> None:
    asyncio.run(_missing_note_becomes_null())


async def _missing_note_becomes_null() -> None:
    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id), None)
    body = _task(subtask_id)
    del body["note"]
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [body],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", subtask_id, "note") is None


def test_add_plan_stores_priority() -> None:
    asyncio.run(_add_plan_stores_priority())


async def _add_plan_stores_priority() -> None:
    source = await prepare_local_source()
    plan_id = await _seed(source, _task(str(uuid.uuid4())), "medium")
    assert await _value(source, "plans", plan_id, "priority") == "medium"


def test_clocks_stay_when_status_unchanged() -> None:
    asyncio.run(_clocks_stay_when_status_unchanged())


async def _clocks_stay_when_status_unchanged() -> None:
    from tests.supabase_plan_db import read_subtask_clocks

    source = await prepare_local_source()
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id), None)
    created_at, status_changed_at = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], subtask_id
    )
    dated = _task(subtask_id, scheduled_on="2026-11-06", effort="S")
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [dated],
            "expected_version": 0,
            "plan_fields": {"priority": "high"},
        },
    )
    same_created, same_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], subtask_id
    )
    assert same_created == created_at
    assert same_status == status_changed_at
    done = dict(dated)
    done["status"] = "done"
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [done],
            "expected_version": 1,
            "plan_fields": {"priority": "high"},
        },
    )
    kept_created, moved_status = await read_subtask_clocks(
        source["SUPABASE_URL"], source["SUPABASE_KEY"], subtask_id
    )
    assert kept_created == created_at
    assert moved_status != status_changed_at


async def _one_move(source: dict[str, str]) -> str:
    subtask_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(subtask_id, scheduled_on="2026-11-06"), None)
    moved = _task(subtask_id, scheduled_on="2026-11-07")
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [moved],
            "expected_version": 0,
            "moved_at": "2026-11-06T08:00:00+02:00",
        },
    )
    from db.client import postgrest_client

    async with postgrest_client(source["SUPABASE_URL"], source["SUPABASE_KEY"]) as client:
        response = await (
            client.from_("subtask_date_moves")
            .select("id")
            .eq("plan_id", plan_id)
            .eq("subtask_id", subtask_id)
            .execute()
        )
    rows = response.data
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise AssertionError("không có đúng một dòng lịch sử")
    move_id = rows[0]["id"]
    if not isinstance(move_id, str):
        raise AssertionError("dòng lịch sử thiếu id")
    return move_id


def test_history_trigger_blocks_update() -> None:
    asyncio.run(_history_trigger_blocks_update())


async def _history_trigger_blocks_update() -> None:
    from postgrest.exceptions import APIError

    from db.client import postgrest_client

    source = await prepare_local_source()
    move_id = await _one_move(source)
    with pytest.raises(APIError):
        async with postgrest_client(source["SUPABASE_URL"], source["SUPABASE_KEY"]) as client:
            await (
                client.from_("subtask_date_moves")
                .update({"reason": "đổi"})
                .eq("id", move_id)
                .execute()
            )
    assert await _value(source, "subtask_date_moves", move_id, "reason") is None


def test_history_trigger_blocks_delete() -> None:
    asyncio.run(_history_trigger_blocks_delete())


async def _history_trigger_blocks_delete() -> None:
    from postgrest.exceptions import APIError

    from db.client import postgrest_client

    source = await prepare_local_source()
    move_id = await _one_move(source)
    with pytest.raises(APIError):
        async with postgrest_client(source["SUPABASE_URL"], source["SUPABASE_KEY"]) as client:
            await client.from_("subtask_date_moves").delete().eq("id", move_id).execute()
    assert await _value(source, "subtask_date_moves", move_id, "to_date") == "2026-11-07"


def test_new_subtask_via_replace_plan_keeps_date_and_effort() -> None:
    asyncio.run(_new_subtask_via_replace_plan_keeps_date_and_effort())


async def _new_subtask_via_replace_plan_keeps_date_and_effort() -> None:
    source = await prepare_local_source()
    existing_id = str(uuid.uuid4())
    added_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(existing_id), None)
    added = _task(added_id, scheduled_on="2026-11-06", effort="M")
    added["title"] = "Mới"
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [_task(existing_id), added],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", added_id, "scheduled_on") == "2026-11-06"
    assert await _value(source, "subtasks", added_id, "effort") == "M"


def test_new_subtask_without_keys_has_null_date_and_effort() -> None:
    asyncio.run(_new_subtask_without_keys_has_null_date_and_effort())


async def _new_subtask_without_keys_has_null_date_and_effort() -> None:
    source = await prepare_local_source()
    existing_id = str(uuid.uuid4())
    added_id = str(uuid.uuid4())
    plan_id = await _seed(source, _task(existing_id, scheduled_on="2026-11-06"), None)
    await _rpc(
        source,
        "replace_plan",
        {
            "plan_id": plan_id,
            "goal": "Mục tiêu",
            "subtasks": [_task(existing_id, scheduled_on="2026-11-06"), _task(added_id)],
            "expected_version": 0,
        },
    )
    assert await _value(source, "subtasks", added_id, "scheduled_on") is None
    assert await _value(source, "subtasks", added_id, "effort") is None
