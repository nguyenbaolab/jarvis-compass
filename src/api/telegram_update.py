"""Điều phối một update Telegram. Không import db, clients, hay config."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.llm import ModelClient, TextMessage
from core.log_line import default_log, error_code_of
from core.morning import is_next_command, render_digest
from core.plans import PlanStore
from core.telegram_channel import (
    CONTEXT_LIMIT,
    CONTEXT_WINDOW,
    DEAD_AFTER,
    Decision,
    TelegramSender,
    UpdateView,
    decide_receive,
    select_context,
    split_utf16,
)
from turns.llm_turn import MissingKeyError, run_turn

_FIXED = "Mình chỉ đọc được tin chữ."
_UNCERTAIN = "Chưa chắc tin này đã được xử lý."

OUTCOME_REJECT = "reject"
OUTCOME_IGNORE = "ignore"
REASON_SECRET_NOT_CONFIGURED = "secret_not_configured"
REASON_SECRET_HEADER_MISSING = "secret_header_missing"
REASON_SECRET_MISMATCH = "secret_mismatch"
REASON_TOKEN_NOT_CONFIGURED = "token_not_configured"
REASON_BODY_UNREADABLE = "body_unreadable"
REASON_OWNER_NOT_CONFIGURED = "owner_not_configured"
REASON_NOT_A_MESSAGE = "not_a_message"
REASON_NOT_PRIVATE_CHAT = "not_private_chat"
REASON_NOT_OWNER = "not_owner"
REASON_BAD_IDS = "bad_ids"
REASON_IN_FLIGHT = "in_flight"
REASON_STORE_UNAVAILABLE = "store_unavailable"
REASON_REPLY_NOT_SAVED = "reply_not_saved"
REASON_CONTEXT_FAILED = "context_failed"
REASON_SEND_FAILED = "send_failed"
REASON_UNEXPECTED = "unexpected"
REASON_REPLIED = "replied"
REASON_RESENT = "resent"
REASON_ALREADY_SENT = "already_sent"
REASON_NON_TEXT = "non_text"
REASON_UNCERTAIN_REPLIED = "uncertain_replied"


class Outcome(Enum):
    Defer = "defer"
    Done = "done"


@dataclass(frozen=True)
class Inbound:
    update_id: int
    chat_id: int
    text: str | None


def _blank(text: str | None) -> bool:
    return text is None or text.strip() == ""


def channel_update_id(payload: object) -> int | None:
    """update_id khi payload là object và mã là int, không phải bool."""

    if not isinstance(payload, dict):
        return None
    update_id = payload.get("update_id")
    if type(update_id) is not int:
        return None
    return update_id


def write_channel_line(
    log: Callable[[str], None] | None,
    outcome: str,
    reason: str,
    update_id: int | None = None,
    error_type: str | None = None,
    error_code: str | None = None,
) -> None:
    """Một dòng JSON của kênh. Không truyền hàm thì in qua default_log."""

    payload: dict[str, object] = {"outcome": outcome, "reason": reason}
    if type(update_id) is int:
        payload["update_id"] = update_id
    if error_type is not None:
        payload["error_type"] = error_type
    if error_code is not None:
        payload["error_code"] = error_code
    writer = default_log if log is None else log
    writer(json.dumps(payload, ensure_ascii=False))


def _caught(error: BaseException) -> tuple[str, str | None]:
    return type(error).__name__, error_code_of(error)


def _note(
    log: Callable[[str], None] | None,
    outcome: Outcome,
    reason: str,
    update_id: int,
    error_type: str | None = None,
    error_code: str | None = None,
) -> None:
    write_channel_line(log, outcome.value, reason, update_id, error_type, error_code)


async def _history(context: object, chat_id: int, now: datetime) -> tuple[TextMessage, ...]:
    rows = await context.list_recent(chat_id, now - CONTEXT_WINDOW, CONTEXT_LIMIT)
    chosen = select_context(rows, now)
    return tuple(TextMessage(role=row.role, text=row.body) for row in chosen)


async def _remember(
    context: object,
    inbound: Inbound,
    reply: str,
    saved_at: datetime,
) -> None:
    if _blank(inbound.text):
        return
    user_text = inbound.text if isinstance(inbound.text, str) else ""
    await context.append_once(inbound.update_id, "user", inbound.chat_id, user_text, saved_at)
    await context.append_once(inbound.update_id, "assistant", inbound.chat_id, reply, saved_at)


async def _deliver(
    sender: TelegramSender,
    updates: object,
    inbound: Inbound,
    reply: str,
    sent_at: datetime,
) -> Outcome:
    for part in split_utf16(reply):
        await sender.send_part(inbound.chat_id, part)
    await updates.mark_sent(inbound.update_id, sent_at)
    return Outcome.Done


async def _save_context_send(
    updates: object,
    context: object,
    sender: TelegramSender,
    inbound: Inbound,
    reply: str,
    saved_at: datetime,
    *,
    remember: bool,
    done_reason: str,
) -> tuple[Outcome, str, str | None, str | None]:
    try:
        saved = await updates.save_reply_if_absent(inbound.update_id, reply)
    except Exception as error:
        return Outcome.Defer, REASON_REPLY_NOT_SAVED, *_caught(error)
    if not saved:
        return Outcome.Defer, REASON_REPLY_NOT_SAVED, None, None
    if remember:
        try:
            await _remember(context, inbound, reply, saved_at)
        except Exception as error:
            return Outcome.Defer, REASON_CONTEXT_FAILED, *_caught(error)
    try:
        delivered = await _deliver(sender, updates, inbound, reply, saved_at)
    except Exception as error:
        return Outcome.Defer, REASON_SEND_FAILED, *_caught(error)
    return delivered, done_reason, None, None


async def _resend(
    updates: object,
    context: object,
    sender: TelegramSender,
    inbound: Inbound,
    reply: str,
    now: datetime,
) -> tuple[Outcome, str, str | None, str | None]:
    try:
        await _remember(context, inbound, reply, now)
    except Exception as error:
        return Outcome.Defer, REASON_CONTEXT_FAILED, *_caught(error)
    try:
        delivered = await _deliver(sender, updates, inbound, reply, now)
    except Exception as error:
        return Outcome.Defer, REASON_SEND_FAILED, *_caught(error)
    return delivered, REASON_RESENT, None, None


async def handle_update(
    inbound: Inbound,
    *,
    open_channel: Callable[[], Awaitable[tuple[object, object]]],
    sender: TelegramSender,
    plans: PlanStore,
    client: ModelClient,
    api_key: str | None,
    clock: Callable[[], datetime],
    log: Callable[[str], None] | None = None,
) -> Outcome:
    """Trả sau khi gửi xong hoặc sau khi đã quyết không gửi."""

    try:
        updates, context = await open_channel()
        now = clock()
        claimed = await updates.claim(inbound.update_id, now)
    except Exception as error:
        error_type, error_code = _caught(error)
        _note(
            log,
            Outcome.Defer,
            REASON_STORE_UNAVAILABLE,
            inbound.update_id,
            error_type,
            error_code,
        )
        return Outcome.Defer

    if not claimed.inserted:
        record = UpdateView(started_at=claimed.started_at, reply=claimed.reply, sent_at=claimed.sent_at)
        decision = decide_receive(record, now, DEAD_AFTER)
        if decision is Decision.Done:
            _note(log, Outcome.Done, REASON_ALREADY_SENT, inbound.update_id)
            return Outcome.Done
        if decision is Decision.Defer:
            _note(log, Outcome.Defer, REASON_IN_FLIGHT, inbound.update_id)
            return Outcome.Defer
        if decision is Decision.Resend and isinstance(claimed.reply, str):
            outcome, reason, error_type, error_code = await _resend(
                updates, context, sender, inbound, claimed.reply, now
            )
            _note(log, outcome, reason, inbound.update_id, error_type, error_code)
            return outcome
        if decision is Decision.SaveUncertain:
            outcome, reason, error_type, error_code = await _save_context_send(
                updates,
                context,
                sender,
                inbound,
                _UNCERTAIN,
                now,
                remember=True,
                done_reason=REASON_UNCERTAIN_REPLIED,
            )
            _note(log, outcome, reason, inbound.update_id, error_type, error_code)
            return outcome
        _note(log, Outcome.Defer, REASON_UNEXPECTED, inbound.update_id)
        return Outcome.Defer

    if _blank(inbound.text):
        outcome, reason, error_type, error_code = await _save_context_send(
            updates,
            context,
            sender,
            inbound,
            _FIXED,
            now,
            remember=False,
            done_reason=REASON_NON_TEXT,
        )
        _note(log, outcome, reason, inbound.update_id, error_type, error_code)
        return outcome

    if is_next_command(inbound.text):
        try:
            stored = await plans.list_newest_first()
        except Exception as error:
            error_type, error_code = _caught(error)
            _note(
                log,
                Outcome.Defer,
                REASON_STORE_UNAVAILABLE,
                inbound.update_id,
                error_type,
                error_code,
            )
            return Outcome.Defer
        outcome, reason, error_type, error_code = await _save_context_send(
            updates,
            context,
            sender,
            inbound,
            render_digest(stored),
            now,
            remember=True,
            done_reason=REASON_REPLIED,
        )
        _note(log, outcome, reason, inbound.update_id, error_type, error_code)
        return outcome

    try:
        history = await _history(context, inbound.chat_id, now)
    except Exception as error:
        error_type, error_code = _caught(error)
        _note(
            log,
            Outcome.Defer,
            REASON_CONTEXT_FAILED,
            inbound.update_id,
            error_type,
            error_code,
        )
        return Outcome.Defer

    try:
        reply = await run_turn(
            inbound.text,
            history,
            instant=now,
            store=plans,
            api_key=api_key,
            client=client,
            log=log,
        )
    except MissingKeyError as error:
        reply = str(error)
    except Exception:
        reply = _UNCERTAIN

    outcome, reason, error_type, error_code = await _save_context_send(
        updates,
        context,
        sender,
        inbound,
        reply,
        clock(),
        remember=True,
        done_reason=REASON_REPLIED,
    )
    _note(log, outcome, reason, inbound.update_id, error_type, error_code)
    return outcome
