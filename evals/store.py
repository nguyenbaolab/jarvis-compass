"""Dựng kho trong bộ nhớ từ bộ dữ liệu đã đọc."""

from datetime import date

from core.plans import (
    Effort,
    Priority,
    Subtask,
    SubtaskStatus,
    new_subtask,
    normalize_new_plan,
    normalize_subtask_note,
)
from tests.fakes.memory_plan_store import MemoryPlanStore

from evals.model import Dataset


async def build_store(dataset: Dataset | None) -> MemoryPlanStore:
    """Mỗi lần gọi trả một kho mới. None là kho không có kế hoạch."""

    store = MemoryPlanStore()
    if dataset is None:
        return store
    for plan in dataset.plans:
        goal_text, _ = normalize_new_plan(plan.goal, None)
        items: list[Subtask] = []
        for seed in plan.subtasks:
            base = new_subtask(seed.title)
            scheduled = date.fromisoformat(seed.scheduled_on) if seed.scheduled_on else None
            effort = Effort(seed.effort) if seed.effort else None
            items.append(
                Subtask(
                    id=base.id,
                    title=base.title,
                    status=SubtaskStatus(seed.status),
                    note=normalize_subtask_note(seed.note),
                    scheduled_on=scheduled,
                    effort=effort,
                )
            )
        priority = Priority(plan.priority) if plan.priority else None
        await store.add(goal_text, tuple(items), priority=priority)
    return store
