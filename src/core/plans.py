"""Model miền kế hoạch và cổng lưu trữ.

Chỉ dùng thư viện chuẩn. Không import FastAPI, Pydantic, tools, hay db.
"""

import re
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Callable, Protocol

import unicodedata


class PlanDomainError(Exception):
    """Lỗi miền khi đầu vào kế hoạch không hợp lệ."""


class PlanConflictError(Exception):
    """Hai lần ghi chạy chồng. Không kế thừa PlanDomainError và không chứa câu người dùng."""


class SubtaskStatus(StrEnum):
    """Trạng thái việc con: pending, done, hoặc skipped."""

    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


class Priority(StrEnum):
    """Ưu tiên của kế hoạch. Không có mức độ gấp."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Effort(StrEnum):
    """Sức của việc con. Số giờ chỉ ở EFFORT_HOURS."""

    S = "S"
    M = "M"
    L = "L"


EFFORT_HOURS: dict[Effort, int] = {Effort.S: 1, Effort.M: 3, Effort.L: 6}

_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_BAD_DATE = "Ngày phải là YYYY-MM-DD."
_BAD_PRIORITY = "Ưu tiên chỉ nhận high, medium hoặc low."
_BAD_EFFORT = "Sức chỉ nhận S, M hoặc L."


@dataclass(frozen=True)
class Subtask:
    """Một việc con. Danh tính giữ nguyên khi trạng thái hoặc ghi chú đổi."""

    id: str
    title: str
    status: SubtaskStatus
    note: str | None
    scheduled_on: date | None = None
    effort: Effort | None = None


@dataclass(frozen=True)
class Plan:
    """Kế hoạch đã lưu. Có mặt trong store nghĩa là đang hoạt động."""

    id: str
    goal: str
    subtasks: tuple[Subtask, ...]
    created_order: int
    version: int
    priority: Priority | None = None


class PlanStore(Protocol):
    """Cổng lưu kế hoạch. Bản cài đặt thật là SupabasePlanStore ở src/db/plan_store.py."""

    async def add(
        self,
        goal: str,
        subtasks: tuple[Subtask, ...],
        *,
        priority: Priority | None = None,
    ) -> Plan:
        """Gán id và created_order, giữ nguyên goal và thứ tự việc con."""

    async def list_newest_first(self) -> tuple[Plan, ...]:
        """Mọi kế hoạch, created_order lớn hơn đứng trước."""

    async def get(self, plan_id: str) -> Plan | None:
        """Trả kế hoạch có đúng id, hoặc None khi không có."""

    async def replace(
        self,
        plan: Plan,
        *,
        move_reason: str | None = None,
        moved_at: datetime | None = None,
    ) -> None:
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


def normalize_scheduled_on(value: object) -> date | None:
    """Ngày lịch YYYY-MM-DD, hoặc trống. Chuỗi khác là lỗi miền."""

    if value is None:
        return None
    if isinstance(value, datetime):
        raise PlanDomainError(_BAD_DATE)
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or _ISO_DATE.fullmatch(value) is None:
        raise PlanDomainError(_BAD_DATE)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise PlanDomainError(_BAD_DATE) from None


def normalize_priority(value: object) -> Priority | None:
    """Ba mã ưu tiên, hoặc trống. Mã lạ là lỗi miền."""

    if value is None:
        return None
    if isinstance(value, Priority):
        return value
    if not isinstance(value, str):
        raise PlanDomainError(_BAD_PRIORITY)
    try:
        return Priority(value)
    except ValueError:
        raise PlanDomainError(_BAD_PRIORITY) from None


def normalize_effort(value: object) -> Effort | None:
    """S, M, L, hoặc trống. Mã lạ là lỗi miền."""

    if value is None:
        return None
    if isinstance(value, Effort):
        return value
    if not isinstance(value, str):
        raise PlanDomainError(_BAD_EFFORT)
    try:
        return Effort(value)
    except ValueError:
        raise PlanDomainError(_BAD_EFFORT) from None


def _subtask_from_raw(raw: object) -> Subtask:
    """Chuỗi là tiêu đề. Object có title, và ngày cùng sức tùy chọn."""

    if isinstance(raw, str):
        return new_subtask(raw)
    if isinstance(raw, dict):
        title = raw.get("title")
        if title is not None and not isinstance(title, str):
            raise PlanDomainError("Việc con không được để trống.")
        built = new_subtask(title)
        return replace(
            built,
            scheduled_on=normalize_scheduled_on(raw.get("scheduled_on")),
            effort=normalize_effort(raw.get("effort")),
        )
    raise PlanDomainError("Việc con không được để trống.")


def normalize_new_plan(
    goal: str | None,
    subtasks: list[str] | list[object] | None,
) -> tuple[str, tuple[Subtask, ...]]:
    """Chuẩn hóa goal và việc con trước khi lưu. Store không chuẩn hóa lại."""

    if goal is None:
        raise PlanDomainError("Mục tiêu không được để trống.")
    normalized_goal = _nfc_strip(goal)
    if normalized_goal == "":
        raise PlanDomainError("Mục tiêu không được để trống.")
    if subtasks is None:
        return normalized_goal, ()
    return normalized_goal, tuple(_subtask_from_raw(raw) for raw in subtasks)


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
        version=plan.version,
        priority=plan.priority,
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


def normalize_move_reason(reason: str | None) -> str | None:
    """NFC rồi bỏ khoảng trắng hai đầu. None hoặc rỗng thành không có lý do."""

    if reason is None:
        return None
    normalized = _nfc_strip(reason)
    if normalized == "":
        return None
    return normalized


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


def plan_deadline(plan: Plan) -> date | None:
    """Ngày muộn nhất trong các việc chưa làm có ngày. Không có thì None."""

    dates = [
        item.scheduled_on
        for item in plan.subtasks
        if item.status is SubtaskStatus.PENDING and item.scheduled_on is not None
    ]
    if not dates:
        return None
    return max(dates)


def deadline_clash(after: Plan, others: tuple[Plan, ...]) -> Plan | None:
    """Kế hoạch khác có cùng hạn. Cùng id với after thì bỏ qua."""

    deadline = plan_deadline(after)
    if deadline is None:
        return None
    for other in others:
        if other.id == after.id:
            continue
        if plan_deadline(other) == deadline:
            return other
    return None


def date_moves(before: Plan, after: Plan) -> tuple[Subtask, ...]:
    """Việc đổi từ một ngày sang một ngày khác. Trả việc ở bản sau."""

    previous = {item.id: item for item in before.subtasks}
    moved: list[Subtask] = []
    for item in after.subtasks:
        old = previous.get(item.id)
        if old is None or old.scheduled_on is None or item.scheduled_on is None:
            continue
        if old.scheduled_on != item.scheduled_on:
            moved.append(item)
    return tuple(moved)


@dataclass(frozen=True)
class DayLoad:
    """Tải tính ra của một ngày. Không lưu trên kế hoạch."""

    total: int
    provisional: int


@dataclass(frozen=True)
class ProposedMove:
    """Một việc code đề xuất dời. Không phải danh sách chủ bot đã chốt."""

    plan_id: str
    subtask_id: str
    title: str
    goal: str
    scheduled_on: date


def day_budget(day: date) -> int:
    """Quỹ giờ của một ngày. Hiện luôn là 8. Không gọi routine."""

    if not isinstance(day, date) or isinstance(day, datetime):
        raise PlanDomainError("Quỹ cần một ngày lịch.")
    return 8


def task_hours(subtask: Subtask) -> int:
    """Giờ của một việc. Xong và bỏ qua là 0. Chưa làm không sức tính 3."""

    if subtask.status is not SubtaskStatus.PENDING:
        return 0
    if subtask.effort is None:
        return EFFORT_HOURS[Effort.M]
    return EFFORT_HOURS[subtask.effort]


def day_load(plans: tuple[Plan, ...], day: date, today: date) -> DayLoad:
    """Tổng giờ và số việc tính tạm của một ngày. Ngày trước hôm nay là 0."""

    if day < today:
        return DayLoad(total=0, provisional=0)
    total = 0
    provisional = 0
    for plan in plans:
        for item in plan.subtasks:
            if item.status is not SubtaskStatus.PENDING or item.scheduled_on != day:
                continue
            total += task_hours(item)
            if item.effort is None:
                provisional += 1
    return DayLoad(total=total, provisional=provisional)


def _move_rank(priority: Priority | None) -> int:
    """Thấp đứng trước. Trống và vừa cùng một mức. Cao đứng sau."""

    if priority is Priority.LOW:
        return 0
    if priority is Priority.HIGH:
        return 2
    return 1


def _move_key(plan: Plan, index: int) -> tuple[int, int, int, int, int]:
    """Hạn muộn hơn trước. Cùng hạn thì tạo trước. Cùng kế hoạch thì việc đứng sau trước."""

    deadline = plan_deadline(plan)
    if deadline is None:
        undated = 1
        later_first = 0
    else:
        undated = 0
        later_first = -deadline.toordinal()
    return (_move_rank(plan.priority), undated, later_first, plan.created_order, -index)


def propose_load_moves(
    plans: tuple[Plan, ...],
    day: date,
    today: date,
    incoming: tuple[tuple[str, str], ...] = (),
) -> tuple[ProposedMove, ...]:
    """Đoạn việc dời ngắn nhất và ngày đích trong bảy ngày sau. Không sửa kế hoạch."""

    load = day_load(plans, day, today)
    budget = day_budget(day)
    if load.total <= budget:
        return ()
    placed = set(incoming)
    candidates: list[tuple[Plan, int, Subtask]] = []
    for plan in plans:
        for index, item in enumerate(plan.subtasks):
            if item.status is not SubtaskStatus.PENDING or item.scheduled_on != day:
                continue
            if (plan.id, item.id) in placed:
                continue
            candidates.append((plan, index, item))
    candidates.sort(key=lambda row: _move_key(row[0], row[1]))
    chosen: list[tuple[Plan, Subtask]] = []
    removed = 0
    cleared = False
    for plan, _index, item in candidates:
        chosen.append((plan, item))
        removed += task_hours(item)
        if load.total - removed <= budget:
            cleared = True
            break
    if not cleared:
        return ()
    assigned: dict[date, int] = {}
    moves: list[ProposedMove] = []
    for plan, item in chosen:
        hours = task_hours(item)
        destination: date | None = None
        for offset in range(1, 8):
            target = day + timedelta(days=offset)
            already = day_load(plans, target, today).total + assigned.get(target, 0)
            if already + hours <= day_budget(target):
                destination = target
                break
        if destination is None:
            continue
        assigned[destination] = assigned.get(destination, 0) + hours
        moves.append(
            ProposedMove(
                plan_id=plan.id,
                subtask_id=item.id,
                title=item.title,
                goal=plan.goal,
                scheduled_on=destination,
            )
        )
    return tuple(moves)


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
