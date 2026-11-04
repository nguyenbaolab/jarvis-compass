"""Điều phối một update Telegram. Không import db, clients, hay config."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.llm import ModelClient, TextMessage
from core.log_line import default_log
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


def _note(log: Callable[[str], None] | None, outcome: Outcome) -> None:
    writer = default_log if log is None else log
    writer(json.dumps({"outcome": outcome.value}, ensure_ascii=False))


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
) -> Outcome:
    try:
        saved = await updates.save_reply_if_absent(inbound.update_id, reply)
    except Exception:
        return Outcome.Defer
    if not saved:
        return Outcome.Defer
    if remember:
        try:
            await _remember(context, inbound, reply, saved_at)
        except Exception:
            return Outcome.Defer
    try:
        return await _deliver(sender, updates, inbound, reply, saved_at)
    except Exception:
        return Outcome.Defer


async def _resend(
    updates: object,
    context: object,
    sender: TelegramSender,
    inbound: Inbound,
    reply: str,
    now: datetime,
) -> Outcome:
    try:
        await _remember(context, inbound, reply, now)
    except Exception:
        return Outcome.Defer
    try:
        return await _deliver(sender, updates, inbound, reply, now)
    except Exception:
        return Outcome.Defer


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
    except Exception:
        _note(log, Outcome.Defer)
        return Outcome.Defer

    if not claimed.inserted:
        record = UpdateView(started_at=claimed.started_at, reply=claimed.reply, sent_at=claimed.sent_at)
        decision = decide_receive(record, now, DEAD_AFTER)
        if decision is Decision.Done:
            _note(log, Outcome.Done)
            return Outcome.Done
        if decision is Decision.Defer:
            _note(log, Outcome.Defer)
            return Outcome.Defer
        if decision is Decision.Resend and isinstance(claimed.reply, str):
            outcome = await _resend(updates, context, sender, inbound, claimed.reply, now)
            _note(log, outcome)
            return outcome
        if decision is Decision.SaveUncertain:
            outcome = await _save_context_send(
                updates,
                context,
                sender,
                inbound,
                _UNCERTAIN,
                now,
                remember=True,
            )
            _note(log, outcome)
            return outcome
        _note(log, Outcome.Defer)
        return Outcome.Defer

    if _blank(inbound.text):
        outcome = await _save_context_send(
            updates,
            context,
            sender,
            inbound,
            _FIXED,
            now,
            remember=False,
        )
        _note(log, outcome)
        return outcome

    try:
        history = await _history(context, inbound.chat_id, now)
    except Exception:
        _note(log, Outcome.Defer)
        return Outcome.Defer

    try:
        reply = await run_turn(
            inbound.text,
            history,
            store=plans,
            api_key=api_key,
            client=client,
            log=log,
        )
    except MissingKeyError as error:
        reply = str(error)
    except Exception:
        reply = _UNCERTAIN

    outcome = await _save_context_send(
        updates,
        context,
        sender,
        inbound,
        reply,
        clock(),
        remember=True,
    )
    _note(log, outcome)
    return outcome
