"""Chỗ duy nhất trong src/ tạo AsyncPostgrestClient."""

from datetime import datetime

import httpx
from postgrest import AsyncPostgrestClient
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_HEADERS
from postgrest.exceptions import APIError


def _headers(key: str) -> dict[str, str]:
    """apikey luôn có. Bearer chỉ khi khóa bắt đầu bằng eyJ."""

    headers = {**DEFAULT_POSTGREST_CLIENT_HEADERS, "apikey": key}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


class StoredPlanMissing(Exception):
    """RPC trả mã plan_missing. Không chứa câu SQL."""


class StoredPlanConflict(Exception):
    """RPC trả plan_version_conflict. Không chứa câu người dùng."""


# Bằng ngân sách của lượt. Trần từng pha HTTP, không bảo đảm FR-001.
_HTTP_CEILING_SECONDS = 20.0


def postgrest_client(url: str, key: str) -> AsyncPostgrestClient:
    """Dựng client. Người gọi dùng async with."""

    base_url = url.rstrip("/") + "/rest/v1"
    headers = _headers(key)
    session = httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=httpx.Timeout(_HTTP_CEILING_SECONDS),
        follow_redirects=True,
        http2=True,
    )
    return AsyncPostgrestClient(base_url, headers=headers, http_client=session)


_PLAN_COLUMNS = (
    "id,goal,created_order,version,"
    "subtasks(id,title,status,note,position,created_at,status_changed_at)"
)


def _rpc_object(data: object) -> dict:
    """RPC jsonb có thể là object hoặc list một phần tử. Không ghi lần hai."""

    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        raise ValueError("RPC không trả một object kế hoạch.")
    if isinstance(data, dict):
        return data
    raise ValueError("RPC không trả object kế hoạch.")


async def add_plan(client: AsyncPostgrestClient, goal: str, subtasks: list[dict]) -> dict:
    """Một RPC add_plan. subtasks là mảng JSON, không phải chuỗi."""

    response = await client.rpc("add_plan", {"goal": goal, "subtasks": subtasks}).execute()
    return _rpc_object(response.data)


async def list_plans(client: AsyncPostgrestClient) -> list:
    """Mọi kế hoạch, created_order lớn hơn đứng trước, việc con theo position."""

    response = (
        await client.from_("plans")
        .select(_PLAN_COLUMNS)
        .order("created_order", desc=True)
        .order("position", foreign_table="subtasks")
        .execute()
    )
    return response.data


async def get_plan(client: AsyncPostgrestClient, plan_id: str) -> dict | None:
    """Một kế hoạch theo id canonical, hoặc None khi maybe_single rỗng."""

    response = (
        await client.from_("plans")
        .select(_PLAN_COLUMNS)
        .eq("id", plan_id)
        .order("position", foreign_table="subtasks")
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    if not isinstance(response.data, dict):
        raise ValueError("get không trả object kế hoạch.")
    return response.data


async def replace_plan(
    client: AsyncPostgrestClient,
    plan_id: str,
    goal: str,
    subtasks: list[dict],
    expected_version: int,
) -> None:
    """Một RPC replace_plan. Hàm SQL trả boolean; giá trị không được đọc, lỗi đi qua APIError."""

    try:
        await client.rpc(
            "replace_plan",
            {
                "plan_id": plan_id,
                "goal": goal,
                "subtasks": subtasks,
                "expected_version": expected_version,
            },
        ).execute()
    except APIError as error:
        if error.message == "plan_missing":
            raise StoredPlanMissing from None
        if error.message == "plan_version_conflict":
            raise StoredPlanConflict from None
        raise


def _rpc_data(data: object) -> object:
    """Bọc list một phần tử của PostgREST. Mảng jsonb nhiều phần tử giữ nguyên."""

    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        return data[0]
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict) and "inserted" in data[0]:
        return data[0]
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], bool):
        return data[0]
    return data


def _stamp(value: datetime) -> str:
    return value.isoformat()


async def claim_telegram_update(
    client: AsyncPostgrestClient,
    update_id: int,
    started_at: datetime,
) -> dict:
    """Một RPC claim. Không select ở Python rồi mới insert."""

    response = await client.rpc(
        "claim_telegram_update",
        {"p_update_id": update_id, "p_started_at": _stamp(started_at)},
    ).execute()
    data = _rpc_data(response.data)
    if not isinstance(data, dict):
        raise ValueError("RPC claim không trả object.")
    return data


async def save_telegram_reply(client: AsyncPostgrestClient, update_id: int, reply: str) -> bool:
    """Một RPC save. Lỗi RPC không thành false."""

    response = await client.rpc(
        "save_telegram_reply",
        {"p_update_id": update_id, "p_reply": reply},
    ).execute()
    return _rpc_data(response.data) is True


async def mark_telegram_sent(
    client: AsyncPostgrestClient,
    update_id: int,
    sent_at: datetime,
) -> None:
    """Một RPC mark. Hàm SQL trả boolean, giá trị không được đọc."""

    await client.rpc(
        "mark_telegram_sent",
        {"p_update_id": update_id, "p_sent_at": _stamp(sent_at)},
    ).execute()


async def append_telegram_context(
    client: AsyncPostgrestClient,
    update_id: int,
    role: str,
    chat_id: int,
    body: str,
    saved_at: datetime,
) -> None:
    """Một RPC append. Trùng khóa thì hàm SQL không đổi body. Hàm SQL trả boolean, giá trị không được đọc."""

    await client.rpc(
        "append_telegram_context",
        {
            "p_update_id": update_id,
            "p_role": role,
            "p_chat_id": chat_id,
            "p_body": body,
            "p_saved_at": _stamp(saved_at),
        },
    ).execute()


async def list_telegram_context(
    client: AsyncPostgrestClient,
    chat_id: int,
    saved_at_gte: datetime,
    limit: int,
) -> list:
    """Một RPC list. Mốc là tham số, không gọi now()."""

    response = await client.rpc(
        "list_telegram_context",
        {
            "p_chat_id": chat_id,
            "p_saved_at_gte": _stamp(saved_at_gte),
            "p_limit": limit,
        },
    ).execute()
    data = _rpc_data(response.data)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("RPC list không trả mảng.")
    return data
