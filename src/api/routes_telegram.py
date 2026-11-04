"""Webhook Telegram. Secret và token trước. Body lạ là Bỏ qua. Không echo."""

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response

from api.telegram_update import Inbound, Outcome, handle_update
from config.settings import (
    SettingsError,
    owner_id_matches,
    require_anthropic_api_key,
    require_telegram_bot_token,
    require_telegram_owner_id,
    require_telegram_webhook_secret,
)

router = APIRouter()


@dataclass
class TelegramDeps:
    env: object
    clock: Callable[[], datetime] | None
    open_channel: object | None
    sender: object | None
    plans: object | None
    model: object | None
    logs: list[str] | None


def header_secret(request: Request) -> object:
    """Giá trị header secret. Test có thể trả giá trị không phải str."""

    return request.headers.get("x-telegram-bot-api-secret-token")


def secrets_match(expected: str, provided: object) -> bool:
    """So hai str bằng hmac.compare_digest. Không phải str, hoặc lỗi so, là không khớp."""

    if not isinstance(provided, str):
        return False
    try:
        return hmac.compare_digest(expected, provided)
    except Exception:
        return False


def current_deps(request: Request) -> TelegramDeps:
    """Cấu hình từ request.scope['env']. Không đọc os.environ."""

    env = request.scope.get("env")
    if env is None:
        env = {}
    return TelegramDeps(
        env=env,
        clock=None,
        open_channel=None,
        sender=None,
        plans=None,
        model=None,
        logs=None,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _inbound(payload: object, owner_id: str) -> Inbound | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        return None
    message = payload["message"]
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None
    if not isinstance(sender, dict) or not owner_id_matches(owner_id, sender.get("id")):
        return None
    update_id = payload.get("update_id")
    chat_id = chat.get("id")
    if isinstance(update_id, bool) or not isinstance(update_id, int):
        return None
    if isinstance(chat_id, bool) or not isinstance(chat_id, int):
        return None
    text = message.get("text")
    if not isinstance(text, str):
        text = None
    return Inbound(update_id=update_id, chat_id=chat_id, text=text)


async def _open_production(env: object) -> tuple[object, object]:
    from db.telegram_channel_store import SupabaseTelegramChannel

    store = SupabaseTelegramChannel(env)
    return store, store


def _empty(status_code: int) -> Response:
    return Response(status_code=status_code)


@router.post("/telegram")
async def telegram_webhook(request: Request, deps: TelegramDeps = Depends(current_deps)) -> Response:
    """Từ chối 401, Hoãn 503, Bỏ qua và xong 200. Body rỗng."""

    try:
        secret = require_telegram_webhook_secret(deps.env)
    except SettingsError:
        return _empty(401)
    if not secrets_match(secret, header_secret(request)):
        return _empty(401)
    try:
        token = require_telegram_bot_token(deps.env)
    except SettingsError:
        return _empty(401)
    try:
        payload = await request.json()
    except Exception:
        return _empty(200)
    try:
        owner_id = require_telegram_owner_id(deps.env)
    except SettingsError:
        return _empty(200)
    inbound = _inbound(payload, owner_id)
    if inbound is None:
        return _empty(200)
    try:
        api_key: str | None = require_anthropic_api_key(deps.env)
    except SettingsError:
        api_key = None
    clock = deps.clock if deps.clock is not None else _utc_now
    try:
        sender = deps.sender
        if sender is None:
            from clients.telegram import TelegramSenderClient

            sender = TelegramSenderClient(token)
        plans = deps.plans
        if plans is None:
            from db.plan_store import SupabasePlanStore

            plans = SupabasePlanStore(deps.env)
        model = deps.model
        if model is None:
            from clients.anthropic_model import AnthropicModel

            model = AnthropicModel()
        open_channel = deps.open_channel
        if open_channel is None:

            async def open_channel() -> tuple[object, object]:
                return await _open_production(deps.env)

        outcome = await handle_update(
            inbound,
            open_channel=open_channel,
            sender=sender,
            plans=plans,
            client=model,
            api_key=api_key,
            clock=clock,
            log=None if deps.logs is None else deps.logs.append,
        )
    except Exception:
        return _empty(503)
    if outcome is Outcome.Defer:
        return _empty(503)
    return _empty(200)
