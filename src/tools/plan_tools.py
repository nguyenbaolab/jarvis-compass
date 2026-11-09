"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from typing import Iterator, TypeVar

from core.plans import (
    Plan,
    PlanConflictError,
    PlanDomainError,
    PlanStore,
    Priority,
    SubtaskStatus,
    append_subtask,
    deadline_clash,
    filter_by_keyword,
    new_subtask,
    normalize_effort,
    normalize_move_reason,
    normalize_new_plan,
    normalize_plan_id,
    normalize_priority,
    normalize_scheduled_on,
    normalize_subtask_id,
    normalize_subtask_note,
    normalize_subtask_status,
    plan_deadline,
    replace_subtask_note,
    replace_subtask_status,
)
from tools.base import Remaining, ToolError, ToolResult, TurnContext, WriteEffect
from tools.saved_reply import (
    REJECTED_SENTENCE,
    UNAVAILABLE_SENTENCE,
    UNCERTAIN_SENTENCE,
    saved_add,
    saved_clear_effort,
    saved_clear_note,
    saved_clear_priority,
    saved_create,
    saved_note,
    saved_reschedule,
    saved_set_effort,
    saved_set_priority,
    saved_status,
)
from tools.schemas import PlanJson, PlansJson, SubtaskJson

_MISSING_PLAN_MESSAGE = "Không có kế hoạch với danh tính này."
_STATUS_LABEL = {
    SubtaskStatus.PENDING: "chưa làm",
    SubtaskStatus.DONE: "xong",
    SubtaskStatus.SKIPPED: "bỏ qua",
}
_PRIORITY_LABEL = {
    Priority.HIGH: "cao",
    Priority.MEDIUM: "vừa",
    Priority.LOW: "thấp",
}
_MISSING_SUBTASK = "Kế hoạch này không có việc con với danh tính này."
_EMPTY_CHANGES = "Cần ít nhất một việc để dời ngày."
_DUPLICATE_CHANGE = "Một việc bị dời hai lần trong cùng lời gọi."
_NEED_TURN = "Cần ngữ cảnh của lượt để dời ngày."
_CONFIRM_SAME_TURN = "Đã báo trùng trong lượt này. Hỏi chủ bot rồi gọi lại ở lượt sau."
_FieldValue = TypeVar("_FieldValue")


def _plan_json(plan: Plan) -> PlanJson:
    """Dựng PlanJson từ một Plan."""

    return PlanJson(
        id=plan.id,
        goal=plan.goal,
        priority=None if plan.priority is None else plan.priority.value,
        subtasks=[
            SubtaskJson(
                id=item.id,
                title=item.title,
                status=item.status.value,
                note=item.note,
                scheduled_on=None if item.scheduled_on is None else item.scheduled_on.isoformat(),
                effort=None if item.effort is None else item.effort.value,
            )
            for item in plan.subtasks
        ],
    )


def _plan_tool_result(plan: Plan, saved: str | None = None) -> ToolResult:
    """Bọc một Plan thành ToolResult thành công. saved là dòng chưa đánh số."""

    body = _plan_json(plan)
    effect = None if saved is None else WriteEffect(kind="saved", text=saved)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False), effect=effect)


@contextmanager
def _domain_as_tool_error() -> Iterator[None]:
    """Đổi PlanDomainError thành ToolError, giữ nguyên câu và nguyên nhân."""

    try:
        yield
    except PlanDomainError as error:
        raise ToolError(str(error)) from error


async def _await_store(remaining: Remaining, call: Callable[[], Awaitable[object]], *, write: bool) -> object:
    """Chờ một lời gọi kho. Số còn lại không dương thì không gửi."""

    if remaining is None:
        return await call()
    seconds = remaining()
    if seconds <= 0:
        raise ToolError(UNAVAILABLE_SENTENCE)
    try:
        return await asyncio.wait_for(call(), seconds)
    except TimeoutError:
        if write:
            raise ToolError(UNCERTAIN_SENTENCE, effect=WriteEffect(kind="uncertain"))
        raise ToolError(UNAVAILABLE_SENTENCE)


async def _replace_plan(
    store: PlanStore,
    plan: Plan,
    remaining: Remaining,
    *,
    move_reason: str | None = None,
    moved_at: datetime | None = None,
) -> None:
    """Một lần replace. Chỉ lời gọi dời ngày truyền lý do và mốc."""

    try:
        if move_reason is None and moved_at is None:
            call = lambda: store.replace(plan)
        else:
            call = lambda: store.replace(plan, move_reason=move_reason, moved_at=moved_at)
        await _await_store(remaining, call, write=True)
    except PlanConflictError:
        raise ToolError(REJECTED_SENTENCE, effect=WriteEffect(kind="rejected")) from None


async def _require_plan(store: PlanStore, plan_id: str, remaining: Remaining) -> Plan:
    """Lấy kế hoạch theo danh tính đã chuẩn hóa. Không có thì ném ToolError."""

    plan = await _await_store(remaining, lambda: store.get(plan_id), write=False)
    if plan is None:
        raise ToolError(_MISSING_PLAN_MESSAGE)
    return plan


def _status_saved_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    return saved_status(item.title, plan.goal, _STATUS_LABEL[item.status])


def _note_saved_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    if item.note:
        return saved_note(item.note, item.title, plan.goal)
    return saved_clear_note(item.title, plan.goal)


async def _replace_subtask_field(
    plan_id: str | None,
    subtask_id: str | None,
    raw_value: str | None,
    store: PlanStore,
    normalize_value: Callable[[str | None], _FieldValue],
    replace_field: Callable[[Plan, str, _FieldValue], Plan],
    remaining: Remaining,
    saved_line: Callable[[Plan, str], str],
) -> ToolResult:
    """Chuẩn hóa ba đầu vào, sửa một việc con, chỉ ghi store khi plan đổi."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized_value = normalize_value(raw_value)
    plan = await _require_plan(store, normalized_plan_id, remaining)
    with _domain_as_tool_error():
        updated = replace_field(plan, normalized_subtask_id, normalized_value)
    if updated is not plan:
        await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, saved_line(updated, normalized_subtask_id))


async def create_plan(
    goal: str | None,
    subtasks: list[str] | list[object] | None = None,
    *,
    priority: str | None = None,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Lưu một kế hoạch đã chuẩn hóa. Không ưu tiên thì add nhận đúng hai tham số vị trí."""

    with _domain_as_tool_error():
        normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
        normalized_priority = normalize_priority(priority)
    if normalized_priority is None:
        call = lambda: store.add(normalized_goal, normalized_subtasks)
    else:
        call = lambda: store.add(
            normalized_goal,
            normalized_subtasks,
            priority=normalized_priority,
        )
    plan = await _await_store(remaining, call, write=True)
    return _plan_tool_result(
        plan,
        saved_create(plan.goal, tuple(item.title for item in plan.subtasks)),
    )


def _plans_json(plans: tuple[Plan, ...]) -> str:
    """Đổi danh sách Plan sang JSON. created_order không có trong JSON."""

    body = PlansJson(plans=[_plan_json(plan) for plan in plans])
    return body.model_dump_json(ensure_ascii=False)


async def get_plans(
    keyword: str | None = None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Liệt kê kế hoạch mới hơn đứng trước, rồi lọc theo từ khóa trong goal hoặc tiêu đề việc con."""

    plans = await _await_store(remaining, store.list_newest_first, write=False)
    listed = filter_by_keyword(plans, keyword)
    return ToolResult(success=True, output=_plans_json(listed))


async def get_plan_detail(
    plan_id: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Mở một kế hoạch theo danh tính đã lưu, hoặc ném ToolError."""

    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
    plan = await _require_plan(store, normalized_id, remaining)
    return _plan_tool_result(plan)


async def update_subtask(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt trạng thái một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return await _replace_subtask_field(
        plan_id,
        subtask_id,
        status,
        store,
        normalize_subtask_status,
        replace_subtask_status,
        remaining,
        _status_saved_line,
    )


async def add_subtask(
    plan_id: str | None,
    title: str | None,
    *,
    scheduled_on: str | None = None,
    effort: str | None = None,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Thêm một việc con vào cuối. Không kiểm trùng và không sinh lịch sử."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        subtask = replace(
            new_subtask(title),
            scheduled_on=normalize_scheduled_on(scheduled_on),
            effort=normalize_effort(effort),
        )
    stored = await _require_plan(store, normalized_plan_id, remaining)
    updated = append_subtask(stored, subtask)
    await _replace_plan(store, updated, remaining)
    added = updated.subtasks[-1]
    return _plan_tool_result(updated, saved_add(added.title, updated.goal))


async def set_subtask_note(
    plan_id: str | None,
    subtask_id: str | None,
    note: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt ghi chú một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return await _replace_subtask_field(
        plan_id,
        subtask_id,
        note,
        store,
        normalize_subtask_note,
        replace_subtask_note,
        remaining,
        _note_saved_line,
    )


def _priority_line(plan: Plan) -> str:
    if plan.priority is None:
        return saved_clear_priority(plan.goal)
    return saved_set_priority(_PRIORITY_LABEL[plan.priority], plan.goal)


async def set_plan_priority(
    plan_id: str | None,
    priority: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt hoặc xóa ưu tiên. Không đụng ngày, sức, hay lịch sử."""

    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
        normalized = normalize_priority(priority)
    plan = await _require_plan(store, normalized_id, remaining)
    if plan.priority == normalized:
        return _plan_tool_result(plan, _priority_line(plan))
    updated = replace(plan, priority=normalized)
    await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, _priority_line(updated))


async def set_subtask_effort(
    plan_id: str | None,
    subtask_id: str | None,
    effort: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt hoặc xóa sức của một việc. Không đụng ưu tiên hay ngày."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized = normalize_effort(effort)
    plan = await _require_plan(store, normalized_plan_id, remaining)
    current = next((item for item in plan.subtasks if item.id == normalized_subtask_id), None)
    if current is None:
        raise PlanDomainError(_MISSING_SUBTASK)
    if current.effort == normalized:
        return _plan_tool_result(
            plan,
            _effort_line(plan, normalized_subtask_id),
        )
    updated_items = tuple(
        replace(item, effort=normalized) if item.id == normalized_subtask_id else item
        for item in plan.subtasks
    )
    updated = replace(plan, subtasks=updated_items)
    await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, _effort_line(updated, normalized_subtask_id))


def _effort_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    if item.effort is None:
        return saved_clear_effort(item.title, plan.goal)
    return saved_set_effort(item.effort.value, item.title, plan.goal)


def _clash_text(other: Plan) -> str:
    deadline = plan_deadline(other)
    if deadline is None:
        raise PlanDomainError("Kế hoạch kia không có hạn.")
    day = deadline.isoformat()
    return (
        f"Lần này chưa ghi. Kế hoạch {other.goal} cũng đến hạn {day}. "
        "Hỏi chủ bot, rồi chỉ gọi lại với confirm ở lượt sau."
    )


def _apply_changes(plan: Plan, changes: list[object]) -> tuple[Plan, tuple[str, ...]]:
    """Dựng kế hoạch sau lần dời. Không ghi. Lỗi miền thì không có bản mới."""

    if not changes:
        raise PlanDomainError(_EMPTY_CHANGES)
    by_id = {item.id: item for item in plan.subtasks}
    seen: set[str] = set()
    updated = dict(by_id)
    titles: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            raise PlanDomainError(_DUPLICATE_CHANGE)
        subtask_id = change.get("subtask_id")
        if not isinstance(subtask_id, str):
            raise PlanDomainError(_MISSING_SUBTASK)
        if subtask_id in seen:
            raise PlanDomainError(_DUPLICATE_CHANGE)
        seen.add(subtask_id)
        if subtask_id not in by_id:
            raise PlanDomainError(_MISSING_SUBTASK)
        scheduled_on = normalize_scheduled_on(change.get("scheduled_on"))
        current = by_id[subtask_id]
        if current.scheduled_on == scheduled_on:
            continue
        titles.append(current.title)
        updated[subtask_id] = replace(current, scheduled_on=scheduled_on)
    subtasks = tuple(updated[item.id] for item in plan.subtasks)
    return replace(plan, subtasks=subtasks), tuple(titles)


async def reschedule_subtasks(
    plan_id: str | None,
    changes: list[object] | None,
    *,
    reason: str | None = None,
    confirm: bool = False,
    store: PlanStore,
    remaining: Remaining = None,
    turn: TurnContext | None = None,
) -> ToolResult:
    """Dời ngày. Không có ngữ cảnh thì không ghi và không đọc đồng hồ."""

    if turn is None:
        raise ToolError(_NEED_TURN)
    if changes is None:
        raise PlanDomainError(_EMPTY_CHANGES)
    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
        normalized_reason = normalize_move_reason(reason)
    plan = await _require_plan(store, normalized_id, remaining)
    updated, titles = _apply_changes(plan, changes)
    if not titles:
        return _plan_tool_result(plan)
    if plan_deadline(plan) != plan_deadline(updated):
        others = await _await_store(remaining, store.list_newest_first, write=False)
        other = deadline_clash(updated, others)
        if other is not None and confirm is not True:
            turn.clash_reported = True
            return ToolResult(success=True, output=_clash_text(other))
        if other is not None and turn.clash_reported:
            raise ToolError(_CONFIRM_SAME_TURN)
    await _replace_plan(
        store,
        updated,
        remaining,
        move_reason=normalized_reason,
        moved_at=turn.instant,
    )
    return _plan_tool_result(updated, saved_reschedule(titles, updated.goal))
