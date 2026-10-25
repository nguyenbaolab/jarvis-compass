"""PlanStore trong bộ nhớ, chỉ cho test. Không đưa class này vào src/."""

import uuid

from core.plans import Plan, PlanDomainError, Subtask


class MemoryPlanStore:
    """Danh sách của đúng instance này. created_order bắt đầu ở 1."""

    def __init__(self) -> None:
        self._plans: list[Plan] = []
        self._next_order = 1

    async def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        """Gán id kế hoạch và created_order. Giữ nguyên id và status của việc con."""

        plan = Plan(
            id=str(uuid.uuid4()),
            goal=goal,
            subtasks=subtasks,
            created_order=self._next_order,
        )
        self._next_order += 1
        self._plans.append(plan)
        return plan

    async def list_newest_first(self) -> tuple[Plan, ...]:
        """created_order lớn hơn đứng trước. Store rỗng trả tuple rỗng."""

        return tuple(sorted(self._plans, key=lambda plan: plan.created_order, reverse=True))

    async def get(self, plan_id: str) -> Plan | None:
        """Trả kế hoạch có id trùng chuỗi được truyền, hoặc None."""

        for plan in self._plans:
            if plan.id == plan_id:
                return plan
        return None

    async def replace(self, plan: Plan) -> None:
        """Thay kế hoạch cùng id. Không thêm mới và không đụng kế hoạch khác."""

        for index, stored in enumerate(self._plans):
            if stored.id == plan.id:
                self._plans[index] = plan
                return
        raise PlanDomainError("Không có kế hoạch với danh tính này.")
