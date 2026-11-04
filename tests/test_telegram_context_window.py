"""Cửa sổ ngữ cảnh: đúng 24 giờ còn, hơn 20 tin thì lấy 20 tin mới nhất."""

from datetime import datetime, timedelta, timezone

from core.telegram_channel import StoredMessage, select_context

_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def test_exactly_24h_kept_older_dropped() -> None:
    kept = StoredMessage(
        saved_at=_NOW - timedelta(hours=24),
        role="user",
        body="đúng mốc",
    )
    dropped = StoredMessage(
        saved_at=_NOW - timedelta(hours=24, seconds=1),
        role="assistant",
        body="cũ hơn",
    )
    chosen = select_context((dropped, kept), _NOW)
    assert chosen == (kept,)


def test_20_newest_messages_old_to_new() -> None:
    rows = tuple(
        StoredMessage(
            saved_at=_NOW - timedelta(minutes=21 - index),
            role="assistant" if index == 1 else "user",
            body=f"m{index}",
        )
        for index in range(21)
    )
    chosen = select_context(rows, _NOW)
    assert len(chosen) == 20
    assert [row.body for row in chosen] == [f"m{index}" for index in range(1, 21)]
    assert chosen[0].role == "assistant"
    assert all(chosen[index].saved_at <= chosen[index + 1].saved_at for index in range(19))
    assert "tin mới" not in [row.body for row in chosen]
