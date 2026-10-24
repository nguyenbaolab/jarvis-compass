"""Hình JSON của tool. Model miền không đặt ở file này."""

from typing import Literal

from pydantic import BaseModel


class SubtaskJson(BaseModel):
    """Một việc con trong JSON của tool. Khóa theo thứ tự id, title, status, note."""

    id: str
    title: str
    status: Literal["pending", "done", "skipped"]
    note: str | None


class PlanJson(BaseModel):
    """Một kế hoạch trong JSON. Đúng ba khóa id, goal, subtasks."""

    id: str
    goal: str
    subtasks: list[SubtaskJson]


class PlansJson(BaseModel):
    """Danh sách kế hoạch. Đúng một khóa plans."""

    plans: list[PlanJson]
