"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

from core.plans import (
    Plan,
    PlanDomainError,
    PlanStore,
    append_subtask,
    filter_by_goal_keyword,
    new_subtask,
    normalize_new_plan,
    normalize_plan_id,
    normalize_subtask_id,
    normalize_subtask_note,
    normalize_subtask_status,
    replace_subtask_note,
    replace_subtask_status,
)
from tools.base import ToolError, ToolResult
from tools.schemas import PlanJson, PlansJson, SubtaskJson

_MISSING_PLAN_MESSAGE = "Không có kế hoạch với danh tính này."
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


def _plan_tool_result(plan: Plan) -> ToolResult:
    """Bọc một Plan thành ToolResult thành công."""

    body = _plan_json(plan)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False))


@contextmanager
def _domain_as_tool_error() -> Iterator[None]:
    """Đổi PlanDomainError thành ToolError, giữ nguyên câu và nguyên nhân."""

    try:
        yield
    except PlanDomainError as error:
        raise ToolError(str(error)) from error


def _require_plan(store: PlanStore, plan_id: str) -> Plan:
    """Lấy kế hoạch theo danh tính đã chuẩn hóa. Không có thì ném ToolError."""

    plan = store.get(plan_id)
    if plan is None:
        raise ToolError(_MISSING_PLAN_MESSAGE)
    return plan


def _replace_subtask_field(
    plan_id: str | None,
    subtask_id: str | None,
    raw_value: str | None,
    store: PlanStore,
    normalize_value: Callable[[str | None], _FieldValue],
    replace_field: Callable[[Plan, str, _FieldValue], Plan],
) -> ToolResult:
    """Chuẩn hóa ba đầu vào, sửa một việc con, chỉ ghi store khi plan đổi."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized_value = normalize_value(raw_value)
    plan = _require_plan(store, normalized_plan_id)
    with _domain_as_tool_error():
        updated = replace_field(plan, normalized_subtask_id, normalized_value)
    if updated is not plan:
        store.replace(updated)
    return _plan_tool_result(updated)


def create_plan(
    goal: str | None,
    subtasks: list[str] | None = None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Lưu một kế hoạch đã chuẩn hóa, hoặc ném ToolError và không gọi add."""

    with _domain_as_tool_error():
        normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
    plan = store.add(normalized_goal, normalized_subtasks)
    return _plan_tool_result(plan)


def _plans_json(plans: tuple[Plan, ...]) -> str:
    """Đổi danh sách Plan sang JSON. created_order không có trong JSON."""

    body = PlansJson(plans=[_plan_json(plan) for plan in plans])
    return body.model_dump_json(ensure_ascii=False)


def get_plans(
    keyword: str | None = None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Liệt kê kế hoạch mới hơn đứng trước, rồi lọc theo từ khóa trong goal."""

    plans = filter_by_goal_keyword(store.list_newest_first(), keyword)
    return ToolResult(success=True, output=_plans_json(plans))


def get_plan_detail(
    plan_id: str | None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Mở một kế hoạch theo danh tính đã lưu, hoặc ném ToolError."""

    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
    plan = _require_plan(store, normalized_id)
    return _plan_tool_result(plan)


def update_subtask(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Đặt trạng thái một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return _replace_subtask_field(
        plan_id, subtask_id, status, store, normalize_subtask_status, replace_subtask_status
    )


def add_subtask(
    plan_id: str | None,
    title: str | None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Thêm một việc con vào cuối, hoặc ném ToolError với đúng câu đầu tiên."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        subtask = new_subtask(title)
    stored = _require_plan(store, normalized_plan_id)
    updated = append_subtask(stored, subtask)
    store.replace(updated)
    return _plan_tool_result(updated)


def set_subtask_note(
    plan_id: str | None,
    subtask_id: str | None,
    note: str | None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Đặt ghi chú một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return _replace_subtask_field(
        plan_id, subtask_id, note, store, normalize_subtask_note, replace_subtask_note
    )
