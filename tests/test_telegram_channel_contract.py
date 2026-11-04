"""Hợp đồng claim, lưu câu, và ngữ cảnh. Memory không mở mạng. Supabase skip khi thiếu biến."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from tests.fakes.memory_telegram_channel import MemoryTelegramChannel

_START = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _memory_store() -> MemoryTelegramChannel:
    return MemoryTelegramChannel()


async def _empty_channel_tables(url: str, key: str) -> None:
    """Xóa ngữ cảnh rồi bản ghi update. Chỉ gọi sau khi host đã là local."""

    from db.client import postgrest_client

    async with postgrest_client(url, key) as client:
        await client.from_("telegram_context_messages").delete().not_.is_("update_id", "null").execute()
        await client.from_("telegram_updates").delete().not_.is_("update_id", "null").execute()


async def _supabase_store() -> object:
    from tests.supabase_plan_db import prepare_local_source

    source = await prepare_local_source()
    await _empty_channel_tables(source["SUPABASE_URL"], source["SUPABASE_KEY"])
    from db.telegram_channel_store import SupabaseTelegramChannel

    return SupabaseTelegramChannel(source)


@pytest.fixture(params=["memory", "supabase"])
def channel_store(request: pytest.FixtureRequest) -> object:
    if request.param == "memory":
        return _memory_store()
    return asyncio.run(_supabase_store())


def test_claim_one_insert(channel_store: object) -> None:
    asyncio.run(_claim_one_insert(channel_store))


def test_save_reply_only_when_absent(channel_store: object) -> None:
    asyncio.run(_save_reply_only_when_absent(channel_store))


def test_append_once_does_not_duplicate_role(channel_store: object) -> None:
    asyncio.run(_append_once_does_not_duplicate_role(channel_store))


def test_list_recent_cutoff_and_limit(channel_store: object) -> None:
    asyncio.run(_list_recent_cutoff_and_limit(channel_store))


def test_mark_sent_only_after_reply_and_only_once(channel_store: object) -> None:
    asyncio.run(_mark_sent_only_after_reply_and_only_once(channel_store))


def test_list_recent_includes_exact_cutoff_and_drops_older(channel_store: object) -> None:
    asyncio.run(_list_recent_includes_exact_cutoff_and_drops_older(channel_store))


async def _claim_one_insert(store: object) -> None:
    later = _START + timedelta(seconds=5)
    first, second = await asyncio.gather(
        store.claim(41, _START),
        store.claim(41, later),
    )
    inserted = [item for item in (first, second) if item.inserted]
    assert len(inserted) == 1
    assert first.started_at == inserted[0].started_at
    assert second.started_at == inserted[0].started_at
    assert first.inserted != second.inserted


async def _save_reply_only_when_absent(store: object) -> None:
    await store.claim(42, _START)
    assert await store.save_reply_if_absent(42, "câu một") is True
    assert await store.save_reply_if_absent(42, "câu hai") is False
    claimed = await store.claim(42, _START + timedelta(seconds=9))
    assert claimed.inserted is False
    assert claimed.reply == "câu một"
    assert await store.save_reply_if_absent(99, "không có hàng") is False


async def _append_once_does_not_duplicate_role(store: object) -> None:
    await store.claim(43, _START)
    await store.append_once(43, "user", 7, "thân một", _START)
    await store.append_once(43, "user", 7, "thân hai", _START + timedelta(seconds=1))
    await store.append_once(43, "assistant", 7, "trả lời", _START + timedelta(seconds=2))
    rows = await store.list_recent(7, _START - timedelta(hours=1), 20)
    bodies = {(row.role, row.body) for row in rows}
    assert bodies == {("user", "thân một"), ("assistant", "trả lời")}


async def _list_recent_cutoff_and_limit(store: object) -> None:
    cutoff = _START
    for index in range(21):
        update_id = 100 + index
        await store.claim(update_id, _START)
        await store.append_once(update_id, "user", 8, f"m{index}", cutoff + timedelta(seconds=index))
    rows = await store.list_recent(8, cutoff, 20)
    assert {row.body for row in rows} == {f"m{index}" for index in range(1, 21)}


async def _mark_sent_only_after_reply_and_only_once(store: object) -> None:
    first = _START + timedelta(seconds=2)
    later = _START + timedelta(seconds=9)
    await store.claim(70, _START)
    await store.mark_sent(70, first)
    untouched = await store.claim(70, _START)
    assert untouched.sent_at is None
    assert await store.save_reply_if_absent(70, "câu") is True
    await store.mark_sent(70, first)
    marked = await store.claim(70, _START)
    assert marked.sent_at == first
    await store.mark_sent(70, later)
    again = await store.claim(70, _START)
    assert again.sent_at == first


async def _list_recent_includes_exact_cutoff_and_drops_older(store: object) -> None:
    cutoff = _START
    await store.claim(80, _START)
    await store.append_once(80, "user", 9, "cũ", cutoff - timedelta(seconds=1))
    await store.claim(81, _START)
    await store.append_once(81, "user", 9, "đúng mốc", cutoff)
    for index in range(19):
        update_id = 200 + index
        await store.claim(update_id, _START)
        await store.append_once(
            update_id,
            "assistant",
            9,
            f"mới{index}",
            cutoff + timedelta(seconds=index + 1),
        )
    rows = await store.list_recent(9, cutoff, 20)
    bodies = {row.body for row in rows}
    assert "đúng mốc" in bodies
    assert "cũ" not in bodies
    assert len(rows) == 20
