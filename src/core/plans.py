"""Model miền kế hoạch và cổng lưu trữ.

Chỉ dùng thư viện chuẩn. Không import FastAPI, Pydantic, tools, hay db.
"""

from dataclasses import dataclass
from typing import Protocol

import unicodedata


class PlanDomainError(Exception):
    """Lỗi miền khi đầu vào tạo kế hoạch không hợp lệ."""


@dataclass(frozen=True)
class Subtask:
    """Một việc con. Không có id, hạn chót, mức ưu tiên, hay trạng thái."""

    title: str


@dataclass(frozen=True)
class Plan:
    """Kế hoạch đã lưu. Có mặt trong store nghĩa là đang hoạt động."""

    id: str
    goal: str
    subtasks: tuple[Subtask, ...]
    created_order: int


class PlanStore(Protocol):
    """Cổng lưu kế hoạch. Lát cắt này không có bản cài đặt trong src/."""

    def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        """Gán id và created_order, giữ nguyên goal và thứ tự việc con."""

    def list_newest_first(self) -> tuple[Plan, ...]:
        """Mọi kế hoạch, created_order lớn hơn đứng trước."""


def _nfc_strip(value: str) -> str:
    """Chuẩn hóa NFC rồi bỏ khoảng trắng hai đầu. Khoảng trắng bên trong giữ nguyên."""

    return unicodedata.normalize("NFC", value).strip()


def normalize_new_plan(
    goal: str | None,
    subtasks: list[str] | None,
) -> tuple[str, tuple[Subtask, ...]]:
    """Chuẩn hóa goal và việc con trước khi lưu. Store không chuẩn hóa lại."""

    if goal is None:
        raise PlanDomainError("Mục tiêu không được để trống.")
    normalized_goal = _nfc_strip(goal)
    if normalized_goal == "":
        raise PlanDomainError("Mục tiêu không được để trống.")
    if subtasks is None:
        return normalized_goal, ()
    normalized_subtasks: list[Subtask] = []
    for raw_title in subtasks:
        title = _nfc_strip(raw_title)
        if title == "":
            raise PlanDomainError("Việc con không được để trống.")
        normalized_subtasks.append(Subtask(title=title))
    return normalized_goal, tuple(normalized_subtasks)


def filter_by_goal_keyword(
    plans: tuple[Plan, ...],
    keyword: str | None,
) -> tuple[Plan, ...]:
    """Giữ kế hoạch có từ khóa trong goal. None hoặc rỗng sau NFC rồi strip là không lọc."""

    if keyword is None:
        return plans
    normalized = unicodedata.normalize("NFC", keyword).strip()
    if normalized == "":
        return plans
    needle = normalized.casefold()
    kept: list[Plan] = []
    for plan in plans:
        haystack = unicodedata.normalize("NFC", plan.goal).casefold()
        if needle in haystack:
            kept.append(plan)
    return tuple(kept)
