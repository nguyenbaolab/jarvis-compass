"""Spike tạm: webhook Telegram echo câu chữ. Không đưa token hay secret ra response."""

import hmac
import time
from typing import Any

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter()

_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_TIMEOUT_SECONDS = 10.0


def _elapsed_ms(started: float) -> int:
    """Đổi khoảng perf_counter sang mili giây, làm tròn."""

    return round((time.perf_counter() - started) * 1000)


def _guard(request: Request) -> str | Response:
    """Thiếu env hoặc một trong hai secret thì 503. Header thiếu hoặc sai thì 401."""

    env = request.scope.get("env")
    if env is None:
        return Response(status_code=503)

    webhook_secret = getattr(env, "TELEGRAM_WEBHOOK_SECRET", None)
    bot_token = getattr(env, "TELEGRAM_BOT_TOKEN", None)
    if not isinstance(webhook_secret, str) or webhook_secret == "":
        return Response(status_code=503)
    if not isinstance(bot_token, str) or bot_token == "":
        return Response(status_code=503)

    presented = request.headers.get(_SECRET_HEADER)
    if not isinstance(presented, str):
        return Response(status_code=401)
    try:
        secret_ok = hmac.compare_digest(presented, webhook_secret)
    except Exception:
        secret_ok = False
    if not secret_ok:
        return Response(status_code=401)
    return bot_token


def _with_update_id(body: dict[str, Any], payload: object) -> dict[str, Any]:
    """Gắn update_id khi payload là object và có khóa đó."""

    if isinstance(payload, dict) and "update_id" in payload:
        body["update_id"] = payload["update_id"]
    return body


def _ignored(payload: object, reason: str) -> JSONResponse:
    """200 và không gọi sendMessage. Telegram gửi lại update khi nhận mã khác 2xx."""

    content = _with_update_id({"action": "ignored", "reason": reason}, payload)
    return JSONResponse(status_code=200, content=content)


def _chat_id(message: dict[str, Any]) -> int | None:
    """Lấy message.chat.id khi là int. bool không được tính là id."""

    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    if isinstance(chat_id, bool) or not isinstance(chat_id, int):
        return None
    return chat_id


async def _send_echo(bot_token: str, chat_id: int, text: str) -> dict[str, Any]:
    """POST sendMessage. Chỉ giữ mã HTTP, ok, mili giây, hoặc tên lớp lỗi."""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": "Echo: " + text},
            )
    except Exception as exc:
        return {
            "action": "echoed",
            "reason": type(exc).__name__,
            "send_ms": _elapsed_ms(started),
        }

    send_ok: Any = None
    try:
        parsed = response.json()
    except Exception:
        parsed = None
    if isinstance(parsed, dict) and "ok" in parsed:
        send_ok = parsed["ok"]
    return {
        "action": "echoed",
        "send_status": response.status_code,
        "send_ok": send_ok,
        "send_ms": _elapsed_ms(started),
    }


@router.post("/spike/telegram")
async def spike_telegram(request: Request) -> Response:
    """Secret đúng thì luôn 200. Có message.text thì echo về đúng chat.id."""

    guarded = _guard(request)
    if isinstance(guarded, Response):
        return guarded
    bot_token = guarded

    try:
        payload = await request.json()
    except Exception:
        return _ignored(None, "json không đọc được")
    if not isinstance(payload, dict):
        return _ignored(None, "body không phải object")

    message = payload.get("message")
    if not isinstance(message, dict):
        return _ignored(payload, "không có message")
    text = message.get("text")
    if not isinstance(text, str):
        return _ignored(payload, "không có text")
    chat_id = _chat_id(message)
    if chat_id is None:
        return _ignored(payload, "không có chat.id")

    sent = await _send_echo(bot_token, chat_id, text)
    return JSONResponse(status_code=200, content=_with_update_id(sent, payload))
