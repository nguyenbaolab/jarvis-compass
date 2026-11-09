"""Luật thuần của bản tin sáng. Chỉ thư viện chuẩn. Không import tzdata."""

from datetime import date
from enum import Enum

from core.clock import helsinki_clock, weekday_name_vi
from core.plans import Plan, Subtask, SubtaskStatus
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
            (item for item in plan.subtasks if item.status is SubtaskStatus.PENDING),
            None,
        )
        if pending is None:
            continue
        segments.append(f"{plan.goal}\n{_pending_title(pending)}")
    if not segments:
        return _EMPTY
    return "\n\n".join(segments)


def _pending_title(item: Subtask) -> str:
    """Tiêu đề đã lưu. Có ngày thì thêm đoạn thứ và ngày, không năm."""

    if item.scheduled_on is None:
        return item.title
    day = item.scheduled_on
    return f"{item.title} ({weekday_name_vi(day)} {day.day:02d}/{day.month:02d})"


def is_next_command(text: str) -> bool:
    """Khớp /next sau khi bỏ khoảng trắng hai đầu và không phân biệt hoa thường."""

    return text.strip().casefold() == _NEXT


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
