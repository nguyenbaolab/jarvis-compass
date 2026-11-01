"""Model miền kế hoạch và cổng lưu trữ.

Chỉ dùng thư viện chuẩn. Không import FastAPI, Pydantic, tools, hay db.
"""

import uuid
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable, Protocol

import unicodedata


class PlanDomainError(Exception):
    """Lỗi miền khi đầu vào kế hoạch không hợp lệ."""


class SubtaskStatus(StrEnum):
    """Trạng thái việc con: pending, done, hoặc skipped."""

    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Subtask:
    """Một việc con. Danh tính giữ nguyên khi trạng thái hoặc ghi chú đổi."""

    id: str
    title: str
    status: SubtaskStatus
    note: str | None


@dataclass(frozen=True)
class Plan:
    """Kế hoạch đã lưu. Có mặt trong store nghĩa là đang hoạt động."""

    id: str
    goal: str
    subtasks: tuple[Subtask, ...]
    created_order: int


class PlanStore(Protocol):
    """Cổng lưu kế hoạch. Lát cắt này không có bản cài đặt trong src/."""

    async def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        """Gán id và created_order, giữ nguyên goal và thứ tự việc con."""

    async def list_newest_first(self) -> tuple[Plan, ...]:
        """Mọi kế hoạch, created_order lớn hơn đứng trước."""

    async def get(self, plan_id: str) -> Plan | None:
        """Trả kế hoạch có đúng id, hoặc None khi không có."""

    async def replace(self, plan: Plan) -> None:
        """Thay kế hoạch cùng id. Không thêm mới và không cấp lại id việc con."""


def _nfc_strip(value: str) -> str:
    """Chuẩn hóa NFC rồi bỏ khoảng trắng hai đầu. Khoảng trắng bên trong giữ nguyên."""

    return unicodedata.normalize("NFC", value).strip()


def new_subtask(title: str | None) -> Subtask:
    """Dựng một việc con mới. None hoặc rỗng sau chuẩn hóa là lỗi miền."""

    if title is None:
        raise PlanDomainError("Việc con không được để trống.")
    normalized = _nfc_strip(title)
    if normalized == "":
        raise PlanDomainError("Việc con không được để trống.")
    return Subtask(
        id=str(uuid.uuid4()),
        title=normalized,
        status=SubtaskStatus.PENDING,
        note=None,
    )


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
    return normalized_goal, tuple(new_subtask(raw_title) for raw_title in subtasks)


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


_INVALID_STATUS_MESSAGE = "Trạng thái việc con chỉ nhận pending, done hoặc skipped."
_MISSING_SUBTASK_MESSAGE = "Kế hoạch này không có việc con với danh tính này."


def normalize_subtask_status(status: str | None) -> SubtaskStatus:
    """Chỉ nhận đúng pending, done hoặc skipped sau khi bỏ khoảng trắng hai đầu."""

    if status is None:
        raise PlanDomainError(_INVALID_STATUS_MESSAGE)
    stripped = status.strip()
    try:
        return SubtaskStatus(stripped)
    except ValueError:
        raise PlanDomainError(_INVALID_STATUS_MESSAGE) from None


def _plan_with_subtasks(plan: Plan, subtasks: tuple[Subtask, ...]) -> Plan:
    """Plan mới cùng id, goal và created_order, với danh sách việc con đã cho."""

    return Plan(
        id=plan.id,
        goal=plan.goal,
        subtasks=subtasks,
        created_order=plan.created_order,
    )


def append_subtask(plan: Plan, subtask: Subtask) -> Plan:
    """Trả về Plan mới, việc con mới đứng cuối. Không chuẩn hóa và không cấp id."""

    return _plan_with_subtasks(plan, plan.subtasks + (subtask,))


def _replace_one_subtask(
    plan: Plan,
    subtask_id: str,
    change: Callable[[Subtask], Subtask],
) -> Plan:
    """Tìm một việc theo id. Không thấy thì lỗi. Việc không đổi thì trả đúng plan."""

    updated: list[Subtask] = []
    found = False
    for item in plan.subtasks:
        if item.id != subtask_id:
            updated.append(item)
            continue
        found = True
        changed = change(item)
        if changed is item:
            return plan
        updated.append(changed)
    if not found:
        raise PlanDomainError(_MISSING_SUBTASK_MESSAGE)
    return _plan_with_subtasks(plan, tuple(updated))


def replace_subtask_status(plan: Plan, subtask_id: str, status: SubtaskStatus) -> Plan:
    """Trả về đúng plan nếu trạng thái không đổi, hoặc plan mới chỉ đổi việc đó."""

    def change(item: Subtask) -> Subtask:
        if item.status == status:
            return item
        return replace(item, status=status)

    return _replace_one_subtask(plan, subtask_id, change)


def normalize_subtask_note(note: str | None) -> str | None:
    """NFC rồi bỏ khoảng trắng hai đầu. None hoặc rỗng thành không có ghi chú."""

    if note is None:
        return None
    normalized = _nfc_strip(note)
    if normalized == "":
        return None
    return normalized


def replace_subtask_note(plan: Plan, subtask_id: str, note: str | None) -> Plan:
    """Trả về đúng plan nếu ghi chú không đổi, hoặc plan mới chỉ đổi việc đó."""

    def change(item: Subtask) -> Subtask:
        if item.note == note:
            return item
        return replace(item, note=note)

    return _replace_one_subtask(plan, subtask_id, change)


def filter_by_keyword(
    plans: tuple[Plan, ...],
    keyword: str | None,
) -> tuple[Plan, ...]:
    """Giữ kế hoạch có từ khóa trong goal hoặc tiêu đề việc con. None hoặc rỗng sau NFC rồi strip là không lọc."""

    def fold(value: str) -> str:
        return unicodedata.normalize("NFC", value).casefold()

    if keyword is None:
        return plans
    normalized = unicodedata.normalize("NFC", keyword).strip()
    if normalized == "":
        return plans
    needle = fold(normalized)
    kept: list[Plan] = []
    for plan in plans:
        matches_title = any(needle in fold(item.title) for item in plan.subtasks)
        if needle in fold(plan.goal) or matches_title:
            kept.append(plan)
    return tuple(kept)
