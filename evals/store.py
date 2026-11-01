"""Dựng kho trong bộ nhớ từ bộ dữ liệu đã đọc."""

from core.plans import Subtask, SubtaskStatus, new_subtask, normalize_new_plan, normalize_subtask_note
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
            items.append(
                Subtask(
                    id=base.id,
                    title=base.title,
                    status=SubtaskStatus(seed.status),
                    note=normalize_subtask_note(seed.note),
                )
            )
        await store.add(goal_text, tuple(items))
    return store
