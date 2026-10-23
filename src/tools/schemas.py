"""Hình JSON của tool. Model miền không đặt ở file này."""

from pydantic import BaseModel


class SubtaskJson(BaseModel):
    """Một việc con trong JSON của tool. Đúng một khóa title."""

    title: str


class PlanJson(BaseModel):
    """Một kế hoạch trong JSON. Đúng ba khóa id, goal, subtasks."""

    id: str
    goal: str
    subtasks: list[SubtaskJson]


class PlansJson(BaseModel):
    """Danh sách kế hoạch. Đúng một khóa plans."""

    plans: list[PlanJson]
