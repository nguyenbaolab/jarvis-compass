"""Helper kho local cho test. Không nằm trong src/. Không đọc .env hay .dev.vars."""

import os
from urllib.parse import urlparse

import httpx
import pytest

from db.client import postgrest_client

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
_HOST_MESSAGE = "Test kho chỉ chạy trên kho local."
_SKIP_DOWN = "Kho local không chạy: không kết nối được."


def require_local_host(url: str, key: str) -> None:
    """Host phải là 127.0.0.1 hoặc localhost. Fail trước khi tạo client."""

    del key
    host = urlparse(url).hostname
    if host is None or host.casefold() not in _LOCAL_HOSTS:
        raise RuntimeError(_HOST_MESSAGE)


def read_test_env() -> tuple[str, str]:
    """Đọc JARVIS_TEST_*. Thiếu thì skip. Không đọc SUPABASE_URL hay SUPABASE_KEY."""

    url = os.environ.get("JARVIS_TEST_SUPABASE_URL")
    key = os.environ.get("JARVIS_TEST_SUPABASE_KEY")
    missing_url = not isinstance(url, str) or url == ""
    missing_key = not isinstance(key, str) or key == ""
    if missing_url and missing_key:
        pytest.skip(
            "Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL và JARVIS_TEST_SUPABASE_KEY."
        )
    if missing_url:
        pytest.skip("Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL.")
    if missing_key:
        pytest.skip("Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_KEY.")
    return url, key


async def empty_plan_tables(url: str, key: str) -> None:
    """Xóa subtasks rồi plans. Chỉ gọi sau khi host đã là local."""

    async with postgrest_client(url, key) as client:
        await client.from_("subtasks").delete().not_.is_("id", "null").execute()
        await client.from_("plans").delete().not_.is_("id", "null").execute()


async def prepare_local_source() -> dict[str, str]:
    """Skip khi thiếu biến hoặc không nối được. Fail khi host không phải local. Rồi xóa hai bảng."""

    url, key = read_test_env()
    require_local_host(url, key)
    try:
        async with postgrest_client(url, key) as client:
            await client.from_("plans").select("id").limit(0).execute()
    except httpx.ConnectError:
        pytest.skip(_SKIP_DOWN)
    except httpx.TimeoutException:
        pytest.skip(_SKIP_DOWN)
    await empty_plan_tables(url, key)
    return {"SUPABASE_URL": url, "SUPABASE_KEY": key}


async def read_subtask_note(url: str, key: str, subtask_id: str) -> object:
    """Đọc cột note bằng client factory. Không thêm hàm này vào src/."""

    async with postgrest_client(url, key) as client:
        response = (
            await client.from_("subtasks")
            .select("note")
            .eq("id", subtask_id)
            .maybe_single()
            .execute()
        )
    if response is None or not isinstance(response.data, dict):
        raise AssertionError("không đọc được dòng việc con")
    return response.data.get("note")


async def read_subtask_clocks(url: str, key: str, subtask_id: str) -> tuple[object, object]:
    """Đọc hai mốc bằng client factory. Không thêm hàm này vào src/."""

    async with postgrest_client(url, key) as client:
        response = (
            await client.from_("subtasks")
            .select("created_at,status_changed_at")
            .eq("id", subtask_id)
            .maybe_single()
            .execute()
        )
    if response is None or not isinstance(response.data, dict):
        raise AssertionError("không đọc được mốc việc con")
    return response.data.get("created_at"), response.data.get("status_changed_at")
