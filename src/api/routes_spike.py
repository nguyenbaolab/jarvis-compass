"""Spike tạm: ghi và đọc Supabase qua PostgREST. Không đưa secret ra response."""

import hmac
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from postgrest import AsyncPostgrestClient
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_HEADERS

router = APIRouter()

_ERROR_LIMIT = 300


def _redact(message: str, secrets: tuple[str, ...]) -> str:
    """Xóa mọi giá trị secret khỏi thông điệp trước khi trả về."""

    cleaned = message
    for secret in sorted({item for item in secrets if item}, key=len, reverse=True):
        cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned[:_ERROR_LIMIT]


def _secret_fragments(url: str, key: str, token: str, base_url: str) -> tuple[str, ...]:
    """Các chuỗi cần xóa khỏi thông điệp lỗi. Không được trả ra ngoài."""

    parts = [url, url.rstrip("/"), base_url, key, token]
    parsed = urlparse(url)
    if parsed.netloc:
        parts.append(parsed.netloc)
    if parsed.hostname:
        parts.append(parsed.hostname)
    return tuple(parts)


def _rows(data: object) -> list[dict[str, object]]:
    """Chỉ giữ id, note, created_at của tối đa ba dòng."""

    if not isinstance(data, list):
        return []
    rows: list[dict[str, object]] = []
    for item in data[:3]:
        if isinstance(item, dict):
            rows.append(
                {
                    "id": item.get("id"),
                    "note": item.get("note"),
                    "created_at": item.get("created_at"),
                }
            )
    return rows


@router.get("/spike/db")
async def spike_db(request: Request) -> Response:
    """Ghi một dòng spike_ping rồi đọc ba dòng mới nhất."""

    env = request.scope.get("env")
    env_in_scope = env is not None
    if env is None:
        return Response(status_code=503)

    token = getattr(env, "SPIKE_TOKEN", None)
    if not isinstance(token, str) or token == "":
        return Response(status_code=503)

    presented = request.headers.get("X-Spike-Token")
    if not isinstance(presented, str):
        return Response(status_code=401)
    try:
        token_ok = hmac.compare_digest(presented, token)
    except Exception:
        token_ok = False
    if not token_ok:
        return Response(status_code=401)

    url_value = getattr(env, "SUPABASE_URL", None)
    key_value = getattr(env, "SUPABASE_KEY", None)
    missing: list[str] = []
    if not isinstance(url_value, str) or url_value == "":
        missing.append("SUPABASE_URL")
    if not isinstance(key_value, str) or key_value == "":
        missing.append("SUPABASE_KEY")
    if missing or not isinstance(url_value, str) or not isinstance(key_value, str):
        return JSONResponse(status_code=503, content={"missing": missing})

    auth_mode = "apikey_only"
    headers = {**DEFAULT_POSTGREST_CLIENT_HEADERS, "apikey": key_value}
    if key_value.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key_value
        auth_mode = "apikey_and_bearer"

    base_url = url_value.rstrip("/") + "/rest/v1"
    note = "spike " + datetime.now(timezone.utc).isoformat()
    secrets = _secret_fragments(url_value, key_value, token, base_url)
    sees_supabase_url = bool(os.getenv("SUPABASE_URL"))

    insert_ok = False
    rows: list[dict[str, object]] = []
    error: dict[str, str] | None = None
    try:
        async with AsyncPostgrestClient(base_url, headers=headers) as client:
            await client.from_("spike_ping").insert({"note": note}).execute()
            insert_ok = True
            read = await (
                client.from_("spike_ping")
                .select("id", "note", "created_at")
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            rows = _rows(read.data)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": _redact(str(exc), secrets)}

    return JSONResponse(
        content={
            "env_in_scope": env_in_scope,
            "os_getenv_sees_supabase_url": sees_supabase_url,
            "auth_mode": auth_mode,
            "insert_ok": insert_ok,
            "rows": rows,
            "error": error,
        }
    )
