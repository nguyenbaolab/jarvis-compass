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
    scheduled_on: str | None = None
    effort: str | None = None


class PlanRow(BaseModel):
    """Một dòng kế hoạch kèm việc con. version là số lần ghi, không phải mốc thời gian."""

    id: str
    goal: str
    created_order: int
    version: int
    priority: str | None = None
    subtasks: list[SubtaskRow]
