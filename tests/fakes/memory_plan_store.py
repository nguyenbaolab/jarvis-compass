"""PlanStore trong bộ nhớ, chỉ cho test. Không đưa class này vào src/."""

import uuid

from core.plans import Plan, Subtask


class MemoryPlanStore:
    """Danh sách của đúng instance này. created_order bắt đầu ở 1."""

    def __init__(self) -> None:
        self._plans: list[Plan] = []
        self._next_order = 1

    def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        """Gán id và created_order. Không chuẩn hóa lại goal hay việc con."""

        plan = Plan(
            id=str(uuid.uuid4()),
            goal=goal,
            subtasks=subtasks,
            created_order=self._next_order,
        )
        self._next_order += 1
        self._plans.append(plan)
        return plan

    def list_newest_first(self) -> tuple[Plan, ...]:
        """created_order lớn hơn đứng trước. Store rỗng trả tuple rỗng."""

        return tuple(sorted(self._plans, key=lambda plan: plan.created_order, reverse=True))
