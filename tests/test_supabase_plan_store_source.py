"""Kho thật dùng địa chỉ và khóa của nguồn người gọi, không đọc sentinel trong env."""

import asyncio

import pytest

from db.plan_store import SupabasePlanStore

_SENTINEL_URL = "https://sentinel.invalid"
_SENTINEL_KEY = "sentinel-key"
_TEST_URL = "http://sentinel-test.invalid"
_TEST_KEY = "sentinel-test-key"


class _Opened:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def _patch_client(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []

    def client(url: str, key: str) -> _Opened:
        seen.append((url, key))
        return _Opened()

    async def list_plans(_client: object) -> list:
        return []

    monkeypatch.setattr("db.plan_store.postgrest_client", client)
    monkeypatch.setattr("db.plan_store.list_plans", list_plans)
    monkeypatch.setenv("SUPABASE_URL", _SENTINEL_URL)
    monkeypatch.setenv("SUPABASE_KEY", _SENTINEL_KEY)
    monkeypatch.setenv("JARVIS_TEST_SUPABASE_URL", _TEST_URL)
    monkeypatch.setenv("JARVIS_TEST_SUPABASE_KEY", _TEST_KEY)
    return seen


def test_dict_source_is_passed_to_client_on_list(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _patch_client(monkeypatch)
    source = {"SUPABASE_URL": "https://caller.invalid", "SUPABASE_KEY": "caller-key"}
    store = SupabasePlanStore(source)
    assert seen == []
    asyncio.run(store.list_newest_first())
    assert seen == [("https://caller.invalid", "caller-key")]


def test_attribute_source_is_passed_to_client_on_list(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _patch_client(monkeypatch)

    class Source:
        SUPABASE_URL = "https://attr.invalid"
        SUPABASE_KEY = "attr-key"

    store = SupabasePlanStore(Source())
    assert seen == []
    asyncio.run(store.list_newest_first())
    assert seen == [("https://attr.invalid", "attr-key")]
