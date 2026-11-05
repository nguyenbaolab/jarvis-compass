"""Webhook Telegram. Secret và token trước. Body lạ là Bỏ qua. Không echo."""

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response

from api.telegram_update import (
    OUTCOME_IGNORE,
    OUTCOME_REJECT,
    REASON_BAD_IDS,
    REASON_BODY_UNREADABLE,
    REASON_NOT_A_MESSAGE,
    REASON_NOT_OWNER,
    REASON_NOT_PRIVATE_CHAT,
    REASON_OWNER_NOT_CONFIGURED,
    REASON_SECRET_HEADER_MISSING,
    REASON_SECRET_MISMATCH,
    REASON_SECRET_NOT_CONFIGURED,
    REASON_TOKEN_NOT_CONFIGURED,
    REASON_UNEXPECTED,
    Inbound,
    Outcome,
    channel_update_id,
    handle_update,
    write_channel_line,
)
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


def _channel_log(
    deps: TelegramDeps,
    outcome: str,
    reason: str,
    update_id: int | None = None,
    error_type: str | None = None,
) -> None:
    write_channel_line(
        None if deps.logs is None else deps.logs.append,
        outcome,
        reason,
        update_id=update_id,
        error_type=error_type,
    )


def _ignore(deps: TelegramDeps, payload: object, reason: str) -> None:
    _channel_log(deps, OUTCOME_IGNORE, reason, update_id=channel_update_id(payload))


def _inbound(deps: TelegramDeps, payload: object, owner_id: str) -> Inbound | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        _ignore(deps, payload, REASON_NOT_A_MESSAGE)
        return None
    message = payload["message"]
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        _ignore(deps, payload, REASON_NOT_PRIVATE_CHAT)
        return None
    if not isinstance(sender, dict) or not owner_id_matches(owner_id, sender.get("id")):
        _channel_log(deps, OUTCOME_IGNORE, REASON_NOT_OWNER, update_id=channel_update_id(payload))
        return None
    update_id = payload.get("update_id")
    chat_id = chat.get("id")
    if isinstance(update_id, bool) or not isinstance(update_id, int):
        _ignore(deps, payload, REASON_BAD_IDS)
        return None
    if isinstance(chat_id, bool) or not isinstance(chat_id, int):
        _ignore(deps, payload, REASON_BAD_IDS)
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
        _channel_log(deps, OUTCOME_REJECT, REASON_SECRET_NOT_CONFIGURED)
        return _empty(401)
    provided = header_secret(request)
    if provided is None:
        _channel_log(deps, OUTCOME_REJECT, REASON_SECRET_HEADER_MISSING)
        return _empty(401)
    if not secrets_match(secret, provided):
        _channel_log(deps, OUTCOME_REJECT, REASON_SECRET_MISMATCH)
        return _empty(401)
    try:
        token = require_telegram_bot_token(deps.env)
    except SettingsError:
        _channel_log(deps, OUTCOME_REJECT, REASON_TOKEN_NOT_CONFIGURED)
        return _empty(401)
    try:
        payload = await request.json()
    except Exception:
        _channel_log(deps, OUTCOME_IGNORE, REASON_BODY_UNREADABLE)
        return _empty(200)
    try:
        owner_id = require_telegram_owner_id(deps.env)
    except SettingsError:
        _channel_log(deps, OUTCOME_IGNORE, REASON_OWNER_NOT_CONFIGURED, update_id=channel_update_id(payload))
        return _empty(200)
    inbound = _inbound(deps, payload, owner_id)
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
    except Exception as error:
        _channel_log(
            deps,
            Outcome.Defer.value,
            REASON_UNEXPECTED,
            update_id=inbound.update_id,
            error_type=type(error).__name__,
        )
        return _empty(503)
    if outcome is Outcome.Defer:
        return _empty(503)
    return _empty(200)
