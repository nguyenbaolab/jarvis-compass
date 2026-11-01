"""Kiểu bộ câu và bộ dữ liệu. Không dùng Pydantic."""

from dataclasses import dataclass
from enum import StrEnum


class Group(StrEnum):
    """Mười nhóm, đúng chữ trong spec."""

    LAP_KE_HOACH = "nhờ lập kế hoạch"
    CHI_KE_VIEC = "chỉ kể việc"
    HOI_DANH_SACH = "hỏi danh sách"
    XEM_CHI_TIET = "xem chi tiết"
    CAP_NHAT = "cập nhật trạng thái việc con"
    THEM_VIEC = "thêm việc con"
    GHI_CHU = "ghi chú"
    CHAO_HOI = "chào hỏi"
    CAU_MO_HO = "câu mơ hồ"
    CAU_NGOAI = "câu ngoài phạm vi"


@dataclass(frozen=True)
class Expectation:
    """Kỳ vọng của một câu. Trường thêm tùy kind."""

    kind: str
    goal: str | None = None
    title: str | None = None
    status: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Case:
    """Một câu đánh giá."""

    id: str
    group: Group
    user_message: str
    dataset: str
    expectation: Expectation


@dataclass(frozen=True)
class SubtaskSeed:
    """Việc con trong file bộ dữ liệu, chưa có id."""

    title: str
    status: str
    note: str | None


@dataclass(frozen=True)
class PlanSeed:
    """Một kế hoạch trong file bộ dữ liệu."""

    goal: str
    subtasks: tuple[SubtaskSeed, ...]


@dataclass(frozen=True)
class Dataset:
    """Một file evals/datasets/<tên>.json đã đọc."""

    name: str
    plans: tuple[PlanSeed, ...]


@dataclass(frozen=True)
class Suite:
    """Bộ câu và các bộ dữ liệu nó trỏ tới."""

    cases_version: int
    cases: tuple[Case, ...]
    datasets: dict[str, Dataset]
