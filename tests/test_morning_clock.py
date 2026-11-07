"""Sáu mốc Helsinki và mã âm của ngày. Không đọc đồng hồ hệ thống."""

import importlib
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from zoneinfo import ZoneInfoNotFoundError

import core.morning as morning
from core.morning import digest_update_id, helsinki_clock

_MARKS = (
    ("2026-01-15T12:00:00+00:00", 2),
    ("2026-07-15T12:00:00+00:00", 3),
    ("2026-03-29T00:59:00+00:00", 2),
    ("2026-03-29T01:00:00+00:00", 3),
    ("2026-10-25T00:59:00+00:00", 3),
    ("2026-10-25T01:00:00+00:00", 2),
)


def test_six_utc_marks_offset_by_two_three_two_three_three_two() -> None:
    hours: list[int] = []
    for raw, _expected in _MARKS:
        instant = datetime.fromisoformat(raw)
        day, local = helsinki_clock(instant)
        utc = instant.astimezone(timezone.utc).replace(tzinfo=None)
        local_naive = datetime.combine(day, local)
        hours.append(int((local_naive - utc).total_seconds() // 3600))
    assert hours == [2, 3, 2, 3, 3, 2]


def test_digest_update_id_of_2026_11_07_is_negative_day_number() -> None:
    day = date(2026, 11, 7)
    assert digest_update_id(day) == -20261107
    assert digest_update_id(day) == -(day.year * 10000 + day.month * 100 + day.day)


def _raise_missing_zone(key: str) -> None:
    raise ZoneInfoNotFoundError(key)


def test_import_does_not_need_zone_data() -> None:
    saved = {
        key: morning.__dict__[key]
        for key in morning.__dict__
        if key not in {"__builtins__"}
    }
    try:
        with patch("zoneinfo.ZoneInfo", new=_raise_missing_zone):
            importlib.reload(morning)
            with pytest.raises(ZoneInfoNotFoundError):
                morning.helsinki_clock(datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))
    finally:
        importlib.reload(morning)
        morning.__dict__.update(saved)
        cached = getattr(morning, "_helsinki_zone", None)
        if cached is not None and hasattr(cached, "cache_clear"):
            cached.cache_clear()
