"""Đồng hồ Helsinki và dòng ngày của một lượt. Không import tzdata."""

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

_WEEKDAYS = (
    "thứ Hai",
    "thứ Ba",
    "thứ Tư",
    "thứ Năm",
    "thứ Sáu",
    "thứ Bảy",
    "Chủ nhật",
)


@lru_cache(maxsize=1)
def _helsinki_zone() -> ZoneInfo:
    """Tạo múi giờ khi có lời gọi. Import module không cần dữ liệu tz."""

    return ZoneInfo("Europe/Helsinki")


def helsinki_clock(instant: datetime) -> tuple[date, time]:
    """Đổi một mốc có múi giờ sang ngày và giờ tường của Europe/Helsinki."""

    if instant.tzinfo is None:
        raise ValueError("instant phải có múi giờ")
    local = instant.astimezone(timezone.utc).astimezone(_helsinki_zone())
    return local.date(), local.timetz().replace(tzinfo=None)


def weekday_name_vi(day: date) -> str:
    """Tên thứ tiếng Việt. Chủ nhật không có chữ thứ đứng trước."""

    return _WEEKDAYS[day.weekday()]


def _week_line(label: str, monday: date) -> str:
    parts = [f"{weekday_name_vi(monday + timedelta(days=offset))} {(monday + timedelta(days=offset)).isoformat()}" for offset in range(7)]
    return f"{label}: {', '.join(parts)}."


def turn_date_line(instant: datetime) -> str:
    """Ba dòng ngày của lượt. Mốc không có múi giờ thì lỗi, không đoán UTC."""

    day, _local_time = helsinki_clock(instant)
    name = weekday_name_vi(day)
    shown = f"{day.day:02d}/{day.month:02d}/{day.year}"
    today = f"Hôm nay là {name} {shown} ({day.isoformat()}), múi giờ Europe/Helsinki."
    monday = day - timedelta(days=day.weekday())
    return "\n".join((today, _week_line("Tuần này", monday), _week_line("Tuần sau", monday + timedelta(days=7))))
