"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

from core.plans import (
    Plan,
    PlanDomainError,
    PlanStore,
    filter_by_goal_keyword,
    normalize_new_plan,
)
from tools.base import ToolError, ToolResult
from tools.schemas import PlanJson, PlansJson, SubtaskJson


def _plan_json(plan: Plan) -> PlanJson:
    """Dựng PlanJson từ một Plan."""

    return PlanJson(
        id=plan.id,
        goal=plan.goal,
        subtasks=[SubtaskJson(title=item.title) for item in plan.subtasks],
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
