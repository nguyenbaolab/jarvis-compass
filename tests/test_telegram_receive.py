"""Ba mốc khoảng chết, tin đã gửi, và câu đã lưu chưa gửi hết."""

from datetime import datetime, timedelta, timezone

from core.telegram_channel import DEAD_AFTER, Decision, UpdateView, decide_receive

_START = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _open(reply: str | None, sent_at: datetime | None = None) -> UpdateView:
    return UpdateView(started_at=_START, reply=reply, sent_at=sent_at)


def test_under_90_seconds_is_defer() -> None:
    now = _START + DEAD_AFTER - timedelta(seconds=1)
    assert decide_receive(_open(None), now, DEAD_AFTER) is Decision.Defer


def test_exactly_90_seconds_is_defer() -> None:
    now = _START + DEAD_AFTER
    assert decide_receive(_open(None), now, DEAD_AFTER) is Decision.Defer


def test_past_90_seconds_is_save_uncertain() -> None:
    now = _START + DEAD_AFTER + timedelta(seconds=1)
    assert decide_receive(_open(None), now, DEAD_AFTER) is Decision.SaveUncertain


def test_sent_record_is_done() -> None:
    now = _START + DEAD_AFTER + timedelta(hours=1)
    assert decide_receive(_open("câu", sent_at=now), now, DEAD_AFTER) is Decision.Done


def test_saved_unsent_is_resend() -> None:
    now = _START + timedelta(seconds=1)
    assert decide_receive(_open("câu"), now, DEAD_AFTER) is Decision.Resend
    assert decide_receive(_open(""), now, DEAD_AFTER) is Decision.Resend
    assert decide_receive(_open(None), now, DEAD_AFTER) is Decision.Defer


def test_dead_after_is_90_seconds() -> None:
    assert DEAD_AFTER == timedelta(seconds=90)
