"""decide_digest không dùng đồng hồ và không có nhánh SaveUncertain."""

from datetime import datetime, timedelta, timezone

from api.telegram_update import _UNCERTAIN
from core.morning import DigestDecision, decide_digest
from core.telegram_channel import DEAD_AFTER, Decision, UpdateView, decide_receive

_STARTED = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)


def _view(*, reply: str | None, sent_at: datetime | None) -> UpdateView:
    return UpdateView(started_at=_STARTED, reply=reply, sent_at=sent_at)


def test_null_reply_after_ninety_seconds_rebuilds() -> None:
    view = _view(reply=None, sent_at=None)
    now = _STARTED + DEAD_AFTER + timedelta(seconds=1)
    assert decide_digest(view) is DigestDecision.Build
    assert decide_receive(view, now, DEAD_AFTER) is Decision.SaveUncertain
    assert _UNCERTAIN == "Chưa chắc tin này đã được xử lý."


def test_sent_at_is_done_without_a_send() -> None:
    view = _view(reply="đã lưu", sent_at=_STARTED)
    assert decide_digest(view) is DigestDecision.Done


def test_stored_reply_is_resent_even_when_older_than_ninety_seconds() -> None:
    view = _view(reply="đã lưu", sent_at=None)
    assert decide_digest(view) is DigestDecision.Resend


def test_decide_digest_has_no_uncertain_branch_and_no_clock() -> None:
    names = {item.name for item in DigestDecision}
    assert "SaveUncertain" not in names
    assert decide_digest.__code__.co_argcount == 1
