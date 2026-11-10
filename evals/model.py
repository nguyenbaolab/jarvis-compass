"""Kiểu bộ câu và bộ dữ liệu. Không dùng Pydantic."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Group(StrEnum):
    """Nhóm câu, đúng chữ trong spec và mục 10a."""

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
    HAN_LUU_NGAY = "hạn tương đối: lưu ngày"
    HAN_HOI_LAI = "hạn tương đối: hỏi lại"
    NHOM_MO_HO = "nhóm việc mơ hồ"
    HAN_CA_KE_HOACH = "hạn cả kế hoạch"
    DOI_HAN_TRUNG = "dời hạn trùng"
    DOI_NGAY = "dời ngày không cần xác nhận"
    TIN_DAI = "tin dài có ngày"
    LIET_KE = "liệt kê tiêu đề"
    GHI_NHAN = "ghi nhận"
    UU_TIEN_NGUOI_DUNG = "ưu tiên do người dùng nêu"
    DAT_UU_TIEN = "đặt ưu tiên"
    DAT_SUC = "đặt sức"
    QUA_TRONG_QUY = "quét tải: trong quỹ"
    QUA_VUOT = "quét tải: vượt quỹ"
    QUA_XONG = "quét tải: việc xong"
    QUA_SUC = "quét tải: sức"
    QUA_CAU = "quét tải: câu cảnh báo"
    QUA_THU_TU = "quét tải: thứ tự dời"
    QUA_XAC_NHAN = "quét tải: xác nhận"
    QUA_TU_CHOI = "quét tải: từ chối"


@dataclass(frozen=True)
class Expectation:
    """Kỳ vọng của một câu. Trường thêm tùy kind."""

    kind: str
    goal: str | None = None
    title: str | None = None
    status: str | None = None
    note: str | None = None
    deadline: str | None = None
    titles: tuple[str, ...] | None = None
    other_goal: str | None = None
    dates: tuple[tuple[str, str], ...] | None = None
    history_moves: int | None = None
    priority: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class Case:
    """Một câu đánh giá."""

    id: str
    group: Group
    user_message: str
    dataset: str
    expectation: Expectation
    instant: datetime | None = None
    follow_up: str | None = None


@dataclass(frozen=True)
class SubtaskSeed:
    """Việc con trong file bộ dữ liệu, chưa có id."""

    title: str
    status: str
    note: str | None
    scheduled_on: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class PlanSeed:
    """Một kế hoạch trong file bộ dữ liệu."""

    goal: str
    subtasks: tuple[SubtaskSeed, ...]
    priority: str | None = None


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
