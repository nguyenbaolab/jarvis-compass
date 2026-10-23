"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

from core.plans import (
    Plan,
    PlanDomainError,
    PlanStore,
    filter_by_goal_keyword,
    normalize_new_plan,
    normalize_plan_id,
    normalize_subtask_id,
    normalize_subtask_status,
    replace_subtask_status,
)
from tools.base import ToolError, ToolResult
from tools.schemas import PlanJson, PlansJson, SubtaskJson


def _plan_json(plan: Plan) -> PlanJson:
    """Dựng PlanJson từ một Plan."""

    return PlanJson(
        id=plan.id,
        goal=plan.goal,
        subtasks=[
            SubtaskJson(id=item.id, title=item.title, status=item.status.value)
            for item in plan.subtasks
        ],
    )


def create_plan(
    goal: str | None,
    subtasks: list[str] | None = None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Lưu một kế hoạch đã chuẩn hóa, hoặc ném ToolError và không gọi add."""

    try:
        normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
    except PlanDomainError as error:
        raise ToolError(str(error)) from error
    plan = store.add(normalized_goal, normalized_subtasks)
    body = _plan_json(plan)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False))


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

    try:
        normalized_id = normalize_plan_id(plan_id)
    except PlanDomainError as error:
        raise ToolError(str(error)) from error
    plan = store.get(normalized_id)
    if plan is None:
        raise ToolError("Không có kế hoạch với danh tính này.")
    body = _plan_json(plan)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False))


def update_subtask(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    *,
    store: PlanStore,
) -> ToolResult:
    """Đặt trạng thái một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    try:
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized_status = normalize_subtask_status(status)
    except PlanDomainError as error:
        raise ToolError(str(error)) from error
    plan = store.get(normalized_plan_id)
    if plan is None:
        raise ToolError("Không có kế hoạch với danh tính này.")
    try:
        updated = replace_subtask_status(
            plan, normalized_subtask_id, normalized_status
        )
    except PlanDomainError as error:
        raise ToolError(str(error)) from error
    if updated is not plan:
        store.replace(updated)
    body = _plan_json(updated)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False))
