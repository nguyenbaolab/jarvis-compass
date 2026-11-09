"""Ba câu và mười một mẫu khi lượt không kết thúc bình thường. Không bản sao ở chỗ khác."""

from collections.abc import Sequence
from dataclasses import dataclass

UNCERTAIN_SENTENCE = "Chưa chắc thay đổi đã được lưu."
REJECTED_SENTENCE = "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."
UNAVAILABLE_SENTENCE = "Không thực hiện được yêu cầu này."


def saved_create(goal: str, titles: tuple[str, ...]) -> str:
    """Dòng đã lưu của create_plan. Không việc thì không có cụm với việc."""

    if not titles:
        return f"Đã lưu kế hoạch {goal}."
    return f"Đã lưu kế hoạch {goal} với việc {', '.join(titles)}."


def saved_add(title: str, goal: str) -> str:
    """Dòng đã lưu của add_subtask."""

    return f"Đã lưu việc {title} vào kế hoạch {goal}."


def saved_status(title: str, goal: str, label: str) -> str:
    """Dòng đã lưu của update_subtask. label là chưa làm, xong, hoặc bỏ qua."""

    return f"Đã lưu việc {title} trong kế hoạch {goal} là {label}."


def saved_note(note: str, title: str, goal: str) -> str:
    """Dòng đã lưu khi ghi chú còn chữ."""

    return f"Đã lưu ghi chú {note} cho việc {title} trong kế hoạch {goal}."


def saved_clear_note(title: str, goal: str) -> str:
    """Dòng đã lưu khi xóa ghi chú."""

    return f"Đã bỏ ghi chú của việc {title} trong kế hoạch {goal}."


def saved_set_priority(label: str, goal: str) -> str:
    """Dòng đã lưu khi đặt ưu tiên. label là cao, vừa, hoặc thấp."""

    return f"Đã lưu ưu tiên {label} cho kế hoạch {goal}."


def saved_clear_priority(goal: str) -> str:
    """Dòng đã lưu khi xóa ưu tiên."""

    return f"Đã bỏ ưu tiên của kế hoạch {goal}."


def saved_set_effort(code: str, title: str, goal: str) -> str:
    """Dòng đã lưu khi đặt sức. code là S, M, hoặc L."""

    return f"Đã lưu sức {code} cho việc {title} trong kế hoạch {goal}."


def saved_clear_effort(title: str, goal: str) -> str:
    """Dòng đã lưu khi xóa sức."""

    return f"Đã bỏ sức của việc {title} trong kế hoạch {goal}."


def saved_reschedule(titles: tuple[str, ...], goal: str) -> str:
    """Một dòng cho cả lần dời ngày. Nhiều tiêu đề nối bằng dấu phẩy."""

    return f"Đã lưu ngày của việc {', '.join(titles)} trong kế hoạch {goal}."


@dataclass(frozen=True)
class Saved:
    """Một lần ghi thành công. text là dòng chưa đánh số."""

    text: str


@dataclass(frozen=True)
class Abandoned:
    """Một lần ghi quá hạn."""


@dataclass(frozen=True)
class Rejected:
    """Một lần ghi bị từ chối."""


def compose(effects: Sequence[Saved | Abandoned | Rejected]) -> str:
    """Dòng đã lưu đánh số, rồi câu chưa chắc, rồi câu từ chối. Không dòng trống."""

    lines: list[str] = []
    number = 0
    uncertain = False
    rejected = False
    for effect in effects:
        if isinstance(effect, Saved):
            number += 1
            lines.append(f"{number}. {effect.text}")
        elif isinstance(effect, Abandoned):
            uncertain = True
        elif isinstance(effect, Rejected):
            rejected = True
    if uncertain:
        lines.append(UNCERTAIN_SENTENCE)
    if rejected:
        lines.append(REJECTED_SENTENCE)
    return "\n".join(lines)
