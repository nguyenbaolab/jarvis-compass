"""Luật thuần của bản tin sáng. Chỉ thư viện chuẩn. Không import tzdata."""

from datetime import date, datetime, time, timezone
from enum import Enum
from functools import lru_cache
from zoneinfo import ZoneInfo

from core.plans import Plan, SubtaskStatus
from core.telegram_channel import UpdateView

_EMPTY = "Không còn việc chưa làm."
_NEXT = "/next"


class DigestDecision(Enum):
    """Ba hướng của digest: xong, gửi lại chữ đã lưu, hoặc dựng mới."""

    Done = "done"
    Resend = "resend"
    Build = "build"


def render_digest(plans: tuple[Plan, ...]) -> str:
    """Mục tiêu và việc pending đầu, kế hoạch cũ trước. Không nhận thời điểm."""

    ordered = sorted(plans, key=lambda plan: plan.created_order)
    segments: list[str] = []
    for plan in ordered:
        pending = next(
            (item.title for item in plan.subtasks if item.status is SubtaskStatus.PENDING),
            None,
        )
        if pending is None:
            continue
        segments.append(f"{plan.goal}\n{pending}")
    if not segments:
        return _EMPTY
    return "\n\n".join(segments)


def is_next_command(text: str) -> bool:
    """Khớp /next sau khi bỏ khoảng trắng hai đầu và không phân biệt hoa thường."""

    return text.strip().casefold() == _NEXT


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


def digest_update_id(day: date) -> int:
    """Mã âm của một ngày Helsinki: -(năm * 10000 + tháng * 100 + ngày)."""

    return -(day.year * 10000 + day.month * 100 + day.day)


def decide_digest(view: UpdateView) -> DigestDecision:
    """Đã gửi thì xong. Đã có chữ thì gửi lại. Chưa có chữ thì dựng. Không có đồng hồ."""

    if view.sent_at is not None:
        return DigestDecision.Done
    if view.reply is not None:
        return DigestDecision.Resend
    return DigestDecision.Build
