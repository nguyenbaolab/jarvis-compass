"""Chỗ duy nhất trong src/ tạo AsyncPostgrestClient."""

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


def postgrest_client(url: str, key: str) -> AsyncPostgrestClient:
    """Dựng client. Người gọi dùng async with."""

    base_url = url.rstrip("/") + "/rest/v1"
    return AsyncPostgrestClient(base_url, headers=_headers(key))


_PLAN_COLUMNS = (
    "id,goal,created_order,"
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
) -> None:
    """Một RPC replace_plan. Hàm SQL trả void, nên không đọc giá trị trả về."""

    try:
        await client.rpc(
            "replace_plan",
            {"plan_id": plan_id, "goal": goal, "subtasks": subtasks},
        ).execute()
    except APIError as error:
        if error.message == "plan_missing":
            raise StoredPlanMissing from None
        raise
