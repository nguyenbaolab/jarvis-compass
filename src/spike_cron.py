"""Spike cron check-in: một tin Telegram cố định. Không import workers."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Request

router = APIRouter()


async def send_checkin(env: Any, cron: str, scheduled_time_ms: int | float) -> None:
    """Gửi tin check-in thử, rồi in một dòng JSON không kèm token hay lỗi thư viện."""
    try:
        step = "read_token"
        token = env.TELEGRAM_BOT_TOKEN
        step = "read_chat_id"
        chat_id = env.TELEGRAM_CHAT_ID
        step = "time"
        scheduled_utc = datetime.fromtimestamp(
            scheduled_time_ms / 1000, tz=UTC
        ).isoformat()
        text = (
            f"Check-in thử từ JARVIS. Cron: {cron}. Giờ hẹn UTC: {scheduled_utc}"
        )
        step = "post"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
        step = "log"
        print(
            json.dumps(
                {"event": "spike_cron", "cron": cron, "status_code": response.status_code}
            )
        )
    except Exception as exc:
        if isinstance(exc, AttributeError):
            print(
                json.dumps(
                    {
                        "event": "spike_cron",
                        "cron": cron,
                        "error": "AttributeError",
                        "attr": getattr(exc, "name", None),
                        "obj_type": type(getattr(exc, "obj", None)).__name__,
                        "step": step,
                    }
                )
            )
        else:
            print(
                json.dumps(
                    {
                        "event": "spike_cron",
                        "cron": cron,
                        "error": type(exc).__name__,
                        "step": step,
                    }
                )
            )


@router.get("/spike/env-check")
async def env_check(request: Request) -> dict[str, bool]:
    """Cho biết env có trong scope hay không; không trả giá trị của env."""
    env = request.scope.get("env")
    return {
        "env_in_scope": env is not None,
        "has_chat_id": hasattr(env, "TELEGRAM_CHAT_ID"),
    }
