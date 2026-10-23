"""Model miền kế hoạch và cổng lưu trữ.

Chỉ dùng thư viện chuẩn. Không import FastAPI, Pydantic, tools, hay db.
"""

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import unicodedata


class PlanDomainError(Exception):
    """Lỗi miền khi đầu vào kế hoạch không hợp lệ."""


class SubtaskStatus(StrEnum):
    """Trạng thái việc con. Lát này chỉ pending hoặc done."""

    PENDING = "pending"
    DONE = "done"


@dataclass(frozen=True)
class Subtask:
    """Một việc con. Danh tính giữ nguyên khi trạng thái đổi."""

    id: str
    title: str
    status: SubtaskStatus


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

    def get(self, plan_id: str) -> Plan | None:
        """Trả kế hoạch có đúng id, hoặc None khi không có."""

    def replace(self, plan: Plan) -> None:
        """Thay kế hoạch cùng id. Không thêm mới và không cấp lại id việc con."""


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
        normalized_subtasks.append(
            Subtask(
                id=str(uuid.uuid4()),
                title=title,
                status=SubtaskStatus.PENDING,
            )
        )
    return normalized_goal, tuple(normalized_subtasks)


def normalize_plan_id(plan_id: str | None) -> str:
    """Bỏ khoảng trắng hai đầu của danh tính. None hoặc rỗng sau strip là lỗi miền."""

    if plan_id is None:
        raise PlanDomainError("Danh tính kế hoạch chưa được đưa.")
    stripped = plan_id.strip()
    if stripped == "":
        raise PlanDomainError("Danh tính kế hoạch chưa được đưa.")
    return stripped


def normalize_subtask_id(subtask_id: str | None) -> str:
    """Bỏ khoảng trắng hai đầu của danh tính việc con. Không NFC, không casefold."""

    if subtask_id is None:
        raise PlanDomainError("Danh tính việc con chưa được đưa.")
    stripped = subtask_id.strip()
    if stripped == "":
        raise PlanDomainError("Danh tính việc con chưa được đưa.")
    return stripped


def normalize_subtask_status(status: str | None) -> SubtaskStatus:
    """Chỉ nhận đúng pending hoặc done sau khi bỏ khoảng trắng hai đầu."""

    if status is None:
        raise PlanDomainError("Trạng thái việc con chỉ nhận pending hoặc done.")
    stripped = status.strip()
    try:
        return SubtaskStatus(stripped)
    except ValueError:
        raise PlanDomainError("Trạng thái việc con chỉ nhận pending hoặc done.") from None


def replace_subtask_status(plan: Plan, subtask_id: str, status: SubtaskStatus) -> Plan:
    """Trả về đúng plan nếu trạng thái không đổi, hoặc plan mới chỉ đổi việc đó."""

    updated: list[Subtask] = []
    found = False
    for item in plan.subtasks:
        if item.id != subtask_id:
            updated.append(item)
            continue
        found = True
        if item.status == status:
            return plan
        updated.append(Subtask(id=item.id, title=item.title, status=status))
    if not found:
        raise PlanDomainError("Kế hoạch này không có việc con với danh tính này.")
    return Plan(
        id=plan.id,
        goal=plan.goal,
        subtasks=tuple(updated),
        created_order=plan.created_order,
    )


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
