"""Dòng DB của plans và subtasks. Không dựng Plan."""

from pydantic import BaseModel


class SubtaskRow(BaseModel):
    """Một dòng việc con đọc từ kho. status là str để mã lạ không bị Pydantic chặn."""

    id: str
    title: str
    status: str
    note: str | None = None
    position: int
    created_at: str
    status_changed_at: str


class PlanRow(BaseModel):
    """Một dòng kế hoạch kèm việc con. Không có mốc thời gian của riêng kế hoạch."""

    id: str
    goal: str
    created_order: int
    subtasks: list[SubtaskRow]
