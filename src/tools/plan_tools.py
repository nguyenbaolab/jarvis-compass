"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from typing import Iterator, TypeVar

from core.plans import (
    Plan,
    PlanConflictError,
    PlanDomainError,
    PlanStore,
    SubtaskStatus,
    append_subtask,
    filter_by_keyword,
    new_subtask,
    normalize_new_plan,
    normalize_plan_id,
    normalize_subtask_id,
    normalize_subtask_note,
    normalize_subtask_status,
    replace_subtask_note,
    replace_subtask_status,
)
from tools.base import Remaining, ToolError, ToolResult, WriteEffect
from tools.saved_reply import (
    REJECTED_SENTENCE,
    UNAVAILABLE_SENTENCE,
    UNCERTAIN_SENTENCE,
    saved_add,
    saved_clear_note,
    saved_create,
    saved_note,
    saved_status,
)
from tools.schemas import PlanJson, PlansJson, SubtaskJson

_MISSING_PLAN_MESSAGE = "Không có kế hoạch với danh tính này."
_STATUS_LABEL = {
    SubtaskStatus.PENDING: "chưa làm",
    SubtaskStatus.DONE: "xong",
    SubtaskStatus.SKIPPED: "bỏ qua",
}
_FieldValue = TypeVar("_FieldValue")


def _plan_json(plan: Plan) -> PlanJson:
    """Dựng PlanJson từ một Plan."""

    return PlanJson(
        id=plan.id,
        goal=plan.goal,
        subtasks=[
            SubtaskJson(
                id=item.id,
                title=item.title,
                status=item.status.value,
                note=item.note,
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


async def _replace_plan(store: PlanStore, plan: Plan, remaining: Remaining) -> None:
    """Một lần replace. Xung đột thành câu từ chối, không gọi lần thứ hai."""

    try:
        await _await_store(remaining, lambda: store.replace(plan), write=True)
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
    subtasks: list[str] | None = None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Lưu một kế hoạch đã chuẩn hóa, hoặc ném ToolError và không gọi add."""

    with _domain_as_tool_error():
        normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
    plan = await _await_store(
        remaining,
        lambda: store.add(normalized_goal, normalized_subtasks),
        write=True,
    )
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
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Thêm một việc con vào cuối, hoặc ném ToolError với đúng câu đầu tiên."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        subtask = new_subtask(title)
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
