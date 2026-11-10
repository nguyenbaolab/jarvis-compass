"""Kho giả, chủ bot gọi execute_tool, và tin sáng lúc 08:00 cố định."""

import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from core.clock import helsinki_clock, weekday_name_vi
from core.plans import (
    Plan,
    append_subtask,
    day_budget,
    day_load,
    new_subtask,
    normalize_effort,
    normalize_new_plan,
    normalize_priority,
    normalize_scheduled_on,
    propose_load_moves,
    task_hours,
)
from scheduler.morning import run_morning
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.fakes.memory_telegram_channel import MemoryTelegramChannel
from tools.base import TurnContext
from tools.tool_router import execute_tool

_HELSINKI = ZoneInfo("Europe/Helsinki")
_MOVE_MARKER = "Nếu vẫn ghi thì dời:"
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def drop(_line: str) -> None:
    """Nuốt nhật ký. Mô phỏng không in dòng JSON của tool."""


def at_helsinki(day: date, hour: int, minute: int = 0) -> datetime:
    """Mốc cố định theo tường Helsinki. Không đọc đồng hồ hệ thống."""

    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=_HELSINKI)


def assert_eight(instant: datetime) -> None:
    """Tin sáng chỉ được gọi đúng 08:00 Helsinki."""

    clock_day, local = helsinki_clock(instant)
    if (local.hour, local.minute, local.second) != (8, 0, 0):
        raise RuntimeError(f"Không phải 08:00 Helsinki: {clock_day.isoformat()} {local}")


def write_crlf(path: Path, text: str) -> None:
    """Ghi UTF-8 với CRLF. Thư mục cha được tạo nếu chưa có."""

    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    path.write_bytes(normalized.replace("\n", "\r\n").encode("utf-8"))


def show_output(output: str) -> str:
    """Chữ tool. JSON thì bỏ khóa id, giữ thứ tự khóa còn lại."""

    stripped = output.strip()
    if not stripped.startswith("{"):
        return output
    try:
        loaded = json.loads(output)
    except json.JSONDecodeError:
        return output
    if not isinstance(loaded, dict):
        return output
    return json.dumps(_strip_ids(loaded), ensure_ascii=False, separators=(",", ":"))


def _strip_ids(value: object) -> object:
    if isinstance(value, dict):
        return {key: _strip_ids(item) for key, item in value.items() if key != "id"}
    if isinstance(value, list):
        return [_strip_ids(item) for item in value]
    return value


def assert_no_ids(text: str) -> None:
    """Bản ghi không được chứa mã sinh ngẫu nhiên."""

    found = _UUID.search(text)
    if found is not None:
        raise RuntimeError(f"Bản ghi có mã: {found.group(0)}")


def fence(text: str) -> str:
    return "```text\n" + text + "\n```"


def day_heading(index: int, day: date) -> str:
    return f"## Ngày {index} — {day.isoformat()} ({weekday_name_vi(day)})"


def sentence_move_count(output: str) -> int:
    """Số việc trong câu dời của tool. Không có đoạn dời thì là 0."""

    if _MOVE_MARKER not in output:
        return 0
    tail = output.split(_MOVE_MARKER, 1)[1]
    return len(re.findall(r"\(kế hoạch .+?\) sang \d{2}/\d{2}\.", tail))


def move_fragment(move: object) -> str:
    """Đoạn tiêu đề và ngày mà câu tool in, không có mã."""

    scheduled = move.scheduled_on
    return (
        f"{move.title} (kế hoạch {move.goal}) sang "
        f"{scheduled.day:02d}/{scheduled.month:02d}"
    )


def describe_moves(moves: tuple[object, ...]) -> str:
    if not moves:
        return "không dời việc nào"
    return "; ".join(
        f"{move.title} (kế hoạch {move.goal}) sang {move.scheduled_on.isoformat()}"
        for move in moves
    )


def moves_payload(moves: tuple[object, ...]) -> list[dict[str, str]]:
    return [
        {
            "plan_id": move.plan_id,
            "subtask_id": move.subtask_id,
            "scheduled_on": move.scheduled_on.isoformat(),
        }
        for move in moves
    ]


def proposed_moves(
    plans: tuple[Plan, ...],
    today: date,
    days: list[date],
    incoming: tuple[tuple[str, str], ...],
) -> tuple[object, ...]:
    """Cùng vòng với tool: từng ngày vượt, propose_load_moves, rồi giữ giờ đã hứa."""

    chosen: list[object] = []
    reserved: dict[date, int] = {}
    for day in sorted(set(days)):
        load = day_load(plans, day, today)
        if load.total <= day_budget(day):
            continue
        moves = propose_load_moves(plans, day, today, incoming, reserved)
        chosen.extend(moves)
        for move in moves:
            source = next(plan for plan in plans if plan.id == move.plan_id)
            task = next(item for item in source.subtasks if item.id == move.subtask_id)
            reserved[move.scheduled_on] = reserved.get(move.scheduled_on, 0) + task_hours(task)
    return tuple(chosen)


async def forecast_create(
    store: object,
    goal: str,
    subtasks: list[object] | None,
    priority: str | None,
    today: date,
) -> tuple[object, ...]:
    plans = await store.list_newest_first()
    normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
    synthetic = Plan(
        id="mới",
        goal=normalized_goal,
        subtasks=normalized_subtasks,
        created_order=0,
        version=0,
        priority=normalize_priority(priority),
    )
    incoming = tuple(("mới", item.id) for item in normalized_subtasks)
    watched = [
        item.scheduled_on
        for item in normalized_subtasks
        if item.scheduled_on is not None and item.scheduled_on >= today
    ]
    return proposed_moves(plans + (synthetic,), today, watched, incoming)


async def forecast_add(
    store: object,
    plan_id: str,
    title: str,
    scheduled_on: str | None,
    effort: str | None,
    today: date,
) -> tuple[object, ...]:
    plans = await store.list_newest_first()
    stored = next(plan for plan in plans if plan.id == plan_id)
    subtask = replace(
        new_subtask(title),
        scheduled_on=normalize_scheduled_on(scheduled_on),
        effort=normalize_effort(effort),
    )
    updated = append_subtask(stored, subtask)
    watched: list[date] = []
    if subtask.scheduled_on is not None and subtask.scheduled_on >= today:
        watched.append(subtask.scheduled_on)
    hypothetical = tuple(updated if plan.id == updated.id else plan for plan in plans)
    return proposed_moves(hypothetical, today, watched, ((updated.id, subtask.id),))


async def forecast_reschedule(
    store: object,
    plan_id: str,
    changes: list[dict[str, object]],
    today: date,
) -> tuple[object, ...]:
    plans = await store.list_newest_first()
    plan = next(item for item in plans if item.id == plan_id)
    wanted = {
        str(change["subtask_id"]): normalize_scheduled_on(change.get("scheduled_on"))
        for change in changes
    }
    updated_items = tuple(
        replace(item, scheduled_on=wanted[item.id]) if item.id in wanted else item
        for item in plan.subtasks
    )
    updated = replace(plan, subtasks=updated_items)
    incoming: list[tuple[str, str]] = []
    watched: list[date] = []
    for old, new in zip(plan.subtasks, updated.subtasks, strict=True):
        if old.scheduled_on == new.scheduled_on:
            continue
        if new.scheduled_on is not None and new.scheduled_on >= today:
            incoming.append((plan.id, new.id))
            watched.append(new.scheduled_on)
    hypothetical = tuple(updated if item.id == updated.id else item for item in plans)
    return proposed_moves(hypothetical, today, watched, tuple(incoming))


async def fingerprint(store: object) -> tuple[object, ...]:
    """Ảnh chụp kho: kế hoạch, việc, và dòng lịch sử. Dùng để so trước sau."""

    plans = await store.list_newest_first()
    body = tuple(
        (
            plan.id,
            plan.goal,
            plan.created_order,
            plan.version,
            None if plan.priority is None else plan.priority.value,
            tuple(
                (
                    item.id,
                    item.title,
                    item.status.value,
                    item.note,
                    None if item.scheduled_on is None else item.scheduled_on.isoformat(),
                    None if item.effort is None else item.effort.value,
                )
                for item in plan.subtasks
            ),
        )
        for plan in plans
    )
    moves = tuple(
        (
            row.plan_id,
            row.subtask_id,
            row.from_date.isoformat(),
            row.to_date.isoformat(),
            row.reason,
            row.moved_at.isoformat(),
        )
        for row in store.date_moves
    )
    return (body, moves)


def format_fingerprint(shot: tuple[object, ...]) -> str:
    body, moves = shot
    lines: list[str] = []
    for plan_id, goal, created_order, version, priority, tasks in body:
        lines.append(
            f"plan {goal!r} version={version} order={created_order} "
            f"priority={priority} id={plan_id}"
        )
        for task_id, title, status, note, day, effort in tasks:
            lines.append(
                f"  task {title!r} status={status} note={note!r} day={day} "
                f"effort={effort} id={task_id}"
            )
    lines.append(f"moves={len(moves)}")
    for move in moves:
        lines.append(f"  {move}")
    return "\n".join(lines)


class RecordingSender:
    """Ghi từng phần tin. Không gửi mạng."""

    def __init__(self) -> None:
        self.parts: list[tuple[int, str]] = []

    async def send_part(self, chat_id: int, text: str) -> None:
        self.parts.append((chat_id, text))


@dataclass(frozen=True)
class MorningSend:
    text: str
    parts: int


class World:
    """Một kho, một kênh, một sender. now do người gọi đưa vào."""

    def __init__(self, store: object) -> None:
        self.store = store
        self.channel = MemoryTelegramChannel()
        self.sender = RecordingSender()

    async def morning(self, instant: datetime) -> MorningSend:
        assert_eight(instant)
        start = len(self.sender.parts)
        await run_morning(
            {"TELEGRAM_OWNER_ID": "123"},
            now=instant,
            plans=self.store,
            channel=self.channel,
            sender=self.sender,
            log=drop,
        )
        sent = self.sender.parts[start:]
        return MorningSend(text="".join(text for _chat, text in sent), parts=len(sent))


class BotOwner:
    """Đọc mã từ get_plans theo tên, rồi gọi execute_tool với JSON đúng lược đồ."""

    def __init__(self, store: object) -> None:
        self.store = store

    async def tool(self, name: str, payload: dict[str, object], instant: datetime):
        return await execute_tool(
            name,
            payload,
            store=self.store,
            log=drop,
            turn=TurnContext(instant=instant),
        )

    async def catalog(self, instant: datetime) -> list[dict[str, object]]:
        result = await self.tool("get_plans", {}, instant)
        if not result.success:
            raise RuntimeError(result.output)
        loaded = json.loads(result.output)
        plans = loaded["plans"]
        if not isinstance(plans, list):
            raise RuntimeError("get_plans không trả danh sách.")
        return plans


def find_plan(catalog: list[dict[str, object]], goal: str) -> dict[str, object]:
    matches = [plan for plan in catalog if plan.get("goal") == goal]
    if len(matches) != 1:
        raise RuntimeError(f"Không thấy đúng một kế hoạch {goal!r}.")
    return matches[0]


def find_task(plan: dict[str, object], title: str) -> dict[str, object]:
    tasks = plan["subtasks"]
    if not isinstance(tasks, list):
        raise RuntimeError("Việc con không phải danh sách.")
    matches = [task for task in tasks if task.get("title") == title]
    if len(matches) != 1:
        raise RuntimeError(f"Không thấy đúng một việc {title!r} trong {plan.get('goal')!r}.")
    return matches[0]


class CountingStore:
    """Bọc MemoryPlanStore. Đếm replace thành công. Có thể ném theo một chế độ đã đặt."""

    def __init__(self, inner: MemoryPlanStore, fail_at: int | None = None) -> None:
        self.inner = inner
        self.fail_at = fail_at
        self.attempts = 0
        self.failures = 0
        self.succeeded: dict[str, int] = {}
        self.history = 0
        self._replaces_this_call = 0
        self._fail_second = False

    def prepare_call(self, *, fail_second_replace: bool = False) -> None:
        """Đặt trước phạm vi một lời gọi. Đếm replace lại từ một."""

        self._replaces_this_call = 0
        self._fail_second = fail_second_replace

    @property
    def date_moves(self):
        return self.inner.date_moves

    async def add(self, goal: str, subtasks: tuple[object, ...], *, priority: object = None):
        if priority is None:
            return await self.inner.add(goal, subtasks)
        return await self.inner.add(goal, subtasks, priority=priority)

    async def list_newest_first(self):
        return await self.inner.list_newest_first()

    async def get(self, plan_id: str):
        return await self.inner.get(plan_id)

    async def replace(self, plan: Plan, *, move_reason: str | None = None, moved_at: datetime | None = None) -> None:
        self.attempts += 1
        self._replaces_this_call += 1
        hit_nth = self.fail_at is not None and self.attempts == self.fail_at
        hit_second = self._fail_second and self._replaces_this_call == 2
        if hit_nth or hit_second:
            self.failures += 1
            self._fail_second = False
            raise RuntimeError("replace đứt")
        before = await self.inner.get(plan.id)
        if before is None:
            raise RuntimeError("replace thiếu kế hoạch")
        await self.inner.replace(plan, move_reason=move_reason, moved_at=moved_at)
        self.succeeded[plan.id] = self.succeeded.get(plan.id, 0) + 1
        self.history += _date_to_date(before, plan)


def _date_to_date(before: Plan, after: Plan) -> int:
    """Việc đổi từ một ngày sang một ngày khác. Đặt lần đầu và bỏ ngày không tính."""

    previous = {item.id: item for item in before.subtasks}
    count = 0
    for item in after.subtasks:
        old = previous.get(item.id)
        if old is None or old.scheduled_on is None or item.scheduled_on is None:
            continue
        if old.scheduled_on != item.scheduled_on:
            count += 1
    return count


class DayClock:
    """Các hành động trong ngày, lệch phút cố định so với 09:00."""

    def __init__(self, day: date) -> None:
        self.day = day
        self.slot = 0

    def next(self) -> datetime:
        instant = at_helsinki(self.day, 9, self.slot * 5)
        self.slot += 1
        if self.slot > 24:
            raise RuntimeError("Quá nhiều mốc trong một ngày.")
        return instant
