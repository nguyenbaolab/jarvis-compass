"""Bản PlanStore trên Supabase. Không import postgrest và không import tools."""

import uuid

from core.plans import Plan, PlanConflictError, PlanDomainError, Subtask, SubtaskStatus
from config.settings import require_supabase
from db.client import (
    StoredPlanConflict,
    StoredPlanMissing,
    add_plan,
    get_plan,
    list_plans,
    postgrest_client,
    replace_plan,
)
from db.models import PlanRow

_BAD_STATUS = "Trạng thái việc con đã lưu không hợp lệ."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_KNOWN_STATUS = frozenset({"pending", "done", "skipped"})


def canonical_plan_id(plan_id: str) -> str | None:
    """Chỉ chuỗi canonical mà str(uuid.UUID) trả về. Khác thì không phải danh tính."""

    try:
        parsed = uuid.UUID(plan_id)
    except (ValueError, AttributeError, TypeError):
        return None
    text = str(parsed)
    if plan_id == text:
        return text
    return None


def _as_text(value: object) -> str:
    return value if isinstance(value, str) else str(value)


def plan_from_row(data: object) -> Plan:
    """Dòng đọc từ kho thành Plan. Thiếu subtasks là lỗi ánh xạ. Mã lạ thì lỗi cả kế hoạch."""

    if not isinstance(data, dict) or "subtasks" not in data:
        raise ValueError("Thiếu khóa subtasks.")
    raw_subtasks = data["subtasks"]
    if not isinstance(raw_subtasks, list):
        raise ValueError("Thiếu khóa subtasks.")
    normalized_subtasks = []
    for item in raw_subtasks:
        if not isinstance(item, dict):
            raise ValueError("Dòng việc con không phải object.")
        copied = dict(item)
        copied["created_at"] = _as_text(copied.get("created_at", ""))
        copied["status_changed_at"] = _as_text(copied.get("status_changed_at", ""))
        if copied.get("note") == "":
            copied["note"] = None
        normalized_subtasks.append(copied)
    row = PlanRow.model_validate(
        {
            "id": _as_text(data["id"]),
            "goal": data["goal"],
            "created_order": int(data["created_order"]),
            "version": int(data["version"]),
            "subtasks": normalized_subtasks,
        }
    )
    ordered = sorted(row.subtasks, key=lambda item: item.position)
    built: list[Subtask] = []
    for item in ordered:
        if item.status not in _KNOWN_STATUS:
            raise PlanDomainError(_BAD_STATUS)
        note = None if item.note in (None, "") else item.note
        built.append(
            Subtask(
                id=item.id,
                title=item.title,
                status=SubtaskStatus(item.status),
                note=note,
            )
        )
    return Plan(
        id=row.id,
        goal=row.goal,
        subtasks=tuple(built),
        created_order=row.created_order,
        version=row.version,
    )


def _subtask_payload(subtasks: tuple[Subtask, ...]) -> list[dict]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "status": item.status.value,
            "note": item.note,
        }
        for item in subtasks
    ]


class SupabasePlanStore:
    """Bốn phương thức cổng. Mỗi lời gọi mở client rồi đóng. Không giữ danh sách."""

    def __init__(self, source: object) -> None:
        self._url, self._key = require_supabase(source)

    async def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        async with postgrest_client(self._url, self._key) as client:
            data = await add_plan(client, goal, _subtask_payload(subtasks))
        return plan_from_row(data)

    async def list_newest_first(self) -> tuple[Plan, ...]:
        async with postgrest_client(self._url, self._key) as client:
            rows = await list_plans(client)
        return tuple(plan_from_row(row) for row in rows)

    async def get(self, plan_id: str) -> Plan | None:
        if canonical_plan_id(plan_id) is None:
            return None
        async with postgrest_client(self._url, self._key) as client:
            row = await get_plan(client, plan_id)
        if row is None:
            return None
        return plan_from_row(row)

    async def replace(self, plan: Plan) -> None:
        if canonical_plan_id(plan.id) is None:
            raise PlanDomainError(_MISSING_PLAN)
        try:
            async with postgrest_client(self._url, self._key) as client:
                await replace_plan(
                    client,
                    plan.id,
                    plan.goal,
                    _subtask_payload(plan.subtasks),
                    plan.version,
                )
        except StoredPlanMissing:
            raise PlanDomainError(_MISSING_PLAN) from None
        except StoredPlanConflict:
            raise PlanConflictError() from None
