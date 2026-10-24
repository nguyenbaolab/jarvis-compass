"""Helper dùng chung cho các bài test kế hoạch."""

import json
import re

import pytest

from core.plans import Plan
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import get_plans, update_subtask

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class ReplaceCounter(MemoryPlanStore):
    """Đếm lần replace trên đúng instance này."""

    def __init__(self) -> None:
        super().__init__()
        self.replace_calls = 0

    def replace(self, plan: Plan) -> None:
        self.replace_calls += 1
        super().replace(plan)


def listed_plans(store: MemoryPlanStore) -> list[dict]:
    result = get_plans(store=store)
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"plans"}
    return data["plans"]


def pending_or_done_plan(result: ToolResult) -> dict:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"id", "goal", "subtasks"}
    assert _UUID.fullmatch(data["id"])
    seen: set[str] = set()
    for item in data["subtasks"]:
        assert list(item) == ["id", "title", "status", "note"]
        assert isinstance(item["title"], str)
        assert item["status"] in {"pending", "done"}
        assert _UUID.fullmatch(item["id"])
        assert item["id"] != data["id"]
        assert item["id"] not in seen
        seen.add(item["id"])
    return data


def pending_plan(result: ToolResult) -> dict:
    assert result.success is True
    data = json.loads(result.output)
    assert set(data) == {"id", "goal", "subtasks"}
    assert _UUID.fullmatch(data["id"])
    seen: set[str] = set()
    for item in data["subtasks"]:
        assert list(item) == ["id", "title", "status", "note"]
        assert isinstance(item["title"], str)
        assert item["status"] == "pending"
        assert _UUID.fullmatch(item["id"])
        assert item["id"] != data["id"]
        assert item["id"] not in seen
        seen.add(item["id"])
    return data


def update_subtask_refusal(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    store: MemoryPlanStore,
) -> str:
    with pytest.raises(ToolError) as caught:
        update_subtask(plan_id, subtask_id, status, store=store)
    return str(caught.value)


def upper_changed(value: str) -> str:
    changed = value.upper()
    assert changed != value
    return changed
