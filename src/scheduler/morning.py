"""Chạy bản tin sáng. Không import workers hay anthropic. Không mở lượt mô hình."""

from collections.abc import Callable
from datetime import datetime, time, timezone

from config.settings import SettingsError, require_telegram_bot_token, require_telegram_owner_id
from core.log_line import default_log, error_code_of, write_json_line
from core.morning import DigestDecision, decide_digest, digest_update_id, helsinki_clock, render_digest
from core.telegram_channel import UpdateView, split_utf16

_EIGHT = time(8, 0)


def _chat_id(env: object) -> int:
    """Số nguyên của TELEGRAM_OWNER_ID. Không strip. '08' không phải '8'."""

    raw = require_telegram_owner_id(env)
    number = int(raw, 10)
    if str(number) != raw:
        raise ValueError("owner")
    return number


def _ports(env: object, plans: object | None, channel: object | None, sender: object | None):
    if plans is None:
        from db.plan_store import SupabasePlanStore

        plans = SupabasePlanStore(env)
    if channel is None:
        from db.telegram_channel_store import SupabaseTelegramChannel

        channel = SupabaseTelegramChannel(env)
    if sender is None:
        from clients.telegram import TelegramSenderClient

        sender = TelegramSenderClient(require_telegram_bot_token(env))
    return plans, channel, sender


def _emit(
    log: Callable[[str], None],
    *,
    outcome: str,
    day: object,
    local: time,
    update_id: int,
    error: BaseException | None,
) -> None:
    error_type = None if error is None else type(error).__name__
    error_code = None if error is None else error_code_of(error)
    write_json_line(
        log,
        {
            "event": "morning_digest",
            "outcome": outcome,
            "helsinki_date": day.isoformat(),
            "local_time": local.strftime("%H:%M"),
            "update_id": update_id,
            "error_type": error_type,
            "error_code": error_code,
        },
    )


async def run_morning(
    env: object,
    *,
    now: datetime | None = None,
    plans: object | None = None,
    channel: object | None = None,
    sender: object | None = None,
    log: Callable[[str], None] | None = None,
) -> None:
    """Trước 08:00 chỉ ghi log. Từ 08:00 claim, rồi gửi hoặc dựng lại theo hàng đã lưu."""

    sink = default_log if log is None else log
    instant = datetime.now(timezone.utc) if now is None else now
    if instant.tzinfo is None:
        raise ValueError("now phải có múi giờ")
    instant = instant.astimezone(timezone.utc)
    day, local = helsinki_clock(instant)
    update_id = digest_update_id(day)
    if local < _EIGHT:
        _emit(sink, outcome="before_eight", day=day, local=local, update_id=update_id, error=None)
        return
    try:
        chat_id = _chat_id(env)
    except (SettingsError, ValueError) as error:
        _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
        return
    try:
        plans, channel, sender = _ports(env, plans, channel, sender)
        claimed = await channel.claim(update_id, instant)
    except Exception as error:
        _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
        return
    decision = decide_digest(
        UpdateView(started_at=claimed.started_at, reply=claimed.reply, sent_at=claimed.sent_at)
    )
    if decision is DigestDecision.Done:
        _emit(sink, outcome="already_sent", day=day, local=local, update_id=update_id, error=None)
        return
    outcome = "sent"
    if decision is DigestDecision.Resend:
        text = claimed.reply
        outcome = "resend"
    else:
        try:
            stored = await plans.list_newest_first()
        except Exception as error:
            _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
            return
        text = render_digest(stored)
        try:
            saved = await channel.save_reply_if_absent(update_id, text)
        except Exception as error:
            _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
            return
        if saved is not True:
            _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=None)
            return
    try:
        await channel.append_once(update_id, "assistant", chat_id, text, instant)
    except Exception as error:
        _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
        return
    try:
        for part in split_utf16(text):
            await sender.send_part(chat_id, part)
    except Exception as error:
        _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
        return
    try:
        await channel.mark_sent(update_id, instant)
    except Exception as error:
        _emit(sink, outcome="deferred", day=day, local=local, update_id=update_id, error=error)
        return
    _emit(sink, outcome=outcome, day=day, local=local, update_id=update_id, error=None)
