"""PlanStore trong bộ nhớ, chỉ cho test. Không đưa class này vào src/."""

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime

from core.plans import Plan, PlanConflictError, PlanDomainError, Priority, Subtask, date_moves

_MOVED_AT_REQUIRED = "Cần mốc khi đổi từ ngày sang ngày."


@dataclass(frozen=True)
class DateMove:
    """Một dòng lịch sử dời ngày trên đúng instance store này."""

    plan_id: str
    subtask_id: str
    from_date: date
    to_date: date
    reason: str | None
    moved_at: datetime


class MemoryPlanStore:
    """Danh sách của đúng instance này. created_order bắt đầu ở 1."""

    def __init__(self) -> None:
        self._plans: list[Plan] = []
        self._next_order = 1
        self.date_moves: list[DateMove] = []

    async def add(
        self,
        goal: str,
        subtasks: tuple[Subtask, ...],
        *,
        priority: Priority | None = None,
    ) -> Plan:
        """Gán id kế hoạch và created_order. Giữ nguyên id và status của việc con."""

        plan = Plan(
            id=str(uuid.uuid4()),
            goal=goal,
            subtasks=subtasks,
            created_order=self._next_order,
            version=0,
            priority=priority,
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

    async def replace(
        self,
        plan: Plan,
        *,
        move_reason: str | None = None,
        moved_at: datetime | None = None,
    ) -> None:
        """Thay kế hoạch cùng id. Đổi từ ngày sang ngày thì cần mốc. Không gọi now."""

        for index, stored in enumerate(self._plans):
            if stored.id != plan.id:
                continue
            if plan.version != stored.version:
                raise PlanConflictError()
            moves = date_moves(stored, plan)
            if moves and moved_at is None:
                raise PlanDomainError(_MOVED_AT_REQUIRED)
            previous = {item.id: item for item in stored.subtasks}
            if moved_at is None:
                stamp = None
            else:
                stamp = moved_at
            for item in moves:
                if stamp is None:
                    raise PlanDomainError(_MOVED_AT_REQUIRED)
                old = previous[item.id]
                assert old.scheduled_on is not None
                assert item.scheduled_on is not None
                self.date_moves.append(
                    DateMove(
                        plan_id=plan.id,
                        subtask_id=item.id,
                        from_date=old.scheduled_on,
                        to_date=item.scheduled_on,
                        reason=move_reason,
                        moved_at=stamp,
                    )
                )
            self._plans[index] = replace(plan, version=plan.version + 1)
            return
        raise PlanDomainError("Không có kế hoạch với danh tính này.")
