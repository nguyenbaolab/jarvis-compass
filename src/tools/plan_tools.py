"""Lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from typing import Iterator, TypeVar

from core.clock import helsinki_clock
from core.plans import (
    DayLoad,
    Plan,
    PlanConflictError,
    PlanDomainError,
    PlanStore,
    Priority,
    ProposedMove,
    Subtask,
    SubtaskStatus,
    append_subtask,
    day_budget,
    day_load,
    task_hours,
    deadline_clash,
    filter_by_keyword,
    new_subtask,
    normalize_effort,
    normalize_move_reason,
    normalize_new_plan,
    normalize_plan_id,
    normalize_priority,
    normalize_scheduled_on,
    normalize_subtask_id,
    normalize_subtask_note,
    normalize_subtask_status,
    plan_deadline,
    propose_load_moves,
    replace_subtask_note,
    replace_subtask_status,
)
from tools.base import Remaining, ToolError, ToolResult, TurnContext, WriteEffect
from tools.saved_reply import (
    REJECTED_SENTENCE,
    UNAVAILABLE_SENTENCE,
    UNCERTAIN_SENTENCE,
    saved_add,
    saved_clear_effort,
    saved_clear_note,
    saved_clear_priority,
    saved_create,
    saved_note,
    saved_reschedule,
    saved_set_effort,
    saved_set_priority,
    saved_status,
)
from tools.schemas import PlanJson, PlansJson, SubtaskJson

_MISSING_PLAN_MESSAGE = "Không có kế hoạch với danh tính này."
_STATUS_LABEL = {
    SubtaskStatus.PENDING: "chưa làm",
    SubtaskStatus.DONE: "xong",
    SubtaskStatus.SKIPPED: "bỏ qua",
}
_PRIORITY_LABEL = {
    Priority.HIGH: "cao",
    Priority.MEDIUM: "vừa",
    Priority.LOW: "thấp",
}
_MISSING_SUBTASK = "Kế hoạch này không có việc con với danh tính này."
_EMPTY_CHANGES = "Cần ít nhất một việc để dời ngày."
_DUPLICATE_CHANGE = "Một việc bị dời hai lần trong cùng lời gọi."
_NEED_TURN = "Cần ngữ cảnh của lượt để dời ngày."
_CONFIRM_SAME_TURN = "Đã báo trùng trong lượt này. Hỏi chủ bot rồi gọi lại ở lượt sau."
_MOVE_GONE = "Việc trong danh sách dời không còn hoặc đã không còn chưa làm."
_Move = tuple[str, str, date]
_FieldValue = TypeVar("_FieldValue")


def _plan_json(plan: Plan) -> PlanJson:
    """Dựng PlanJson từ một Plan."""

    return PlanJson(
        id=plan.id,
        goal=plan.goal,
        priority=None if plan.priority is None else plan.priority.value,
        subtasks=[
            SubtaskJson(
                id=item.id,
                title=item.title,
                status=item.status.value,
                note=item.note,
                scheduled_on=None if item.scheduled_on is None else item.scheduled_on.isoformat(),
                effort=None if item.effort is None else item.effort.value,
            )
            for item in plan.subtasks
        ],
    )


def _plan_tool_result(plan: Plan, saved: str | None = None) -> ToolResult:
    """Bọc một Plan thành ToolResult thành công. saved là dòng chưa đánh số."""

    body = _plan_json(plan)
    effect = None if saved is None else WriteEffect(kind="saved", text=saved)
    return ToolResult(success=True, output=body.model_dump_json(ensure_ascii=False), effect=effect)


@contextmanager
def _domain_as_tool_error() -> Iterator[None]:
    """Đổi PlanDomainError thành ToolError, giữ nguyên câu và nguyên nhân."""

    try:
        yield
    except PlanDomainError as error:
        raise ToolError(str(error)) from error


async def _await_store(remaining: Remaining, call: Callable[[], Awaitable[object]], *, write: bool) -> object:
    """Chờ một lời gọi kho. Số còn lại không dương thì không gửi."""

    if remaining is None:
        return await call()
    seconds = remaining()
    if seconds <= 0:
        raise ToolError(UNAVAILABLE_SENTENCE)
    try:
        return await asyncio.wait_for(call(), seconds)
    except TimeoutError:
        if write:
            raise ToolError(UNCERTAIN_SENTENCE, effect=WriteEffect(kind="uncertain"))
        raise ToolError(UNAVAILABLE_SENTENCE)


async def _replace_plan(
    store: PlanStore,
    plan: Plan,
    remaining: Remaining,
    *,
    move_reason: str | None = None,
    moved_at: datetime | None = None,
) -> None:
    """Một lần replace. Chỉ lời gọi dời ngày truyền lý do và mốc."""

    try:
        if move_reason is None and moved_at is None:
            call = lambda: store.replace(plan)
        else:
            call = lambda: store.replace(plan, move_reason=move_reason, moved_at=moved_at)
        await _await_store(remaining, call, write=True)
    except PlanConflictError:
        raise ToolError(REJECTED_SENTENCE, effect=WriteEffect(kind="rejected")) from None


async def _require_plan(store: PlanStore, plan_id: str, remaining: Remaining) -> Plan:
    """Lấy kế hoạch theo danh tính đã chuẩn hóa. Không có thì ném ToolError."""

    plan = await _await_store(remaining, lambda: store.get(plan_id), write=False)
    if plan is None:
        raise ToolError(_MISSING_PLAN_MESSAGE)
    return plan


def _status_saved_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    return saved_status(item.title, plan.goal, _STATUS_LABEL[item.status])


def _note_saved_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    if item.note:
        return saved_note(item.note, item.title, plan.goal)
    return saved_clear_note(item.title, plan.goal)


async def _replace_subtask_field(
    plan_id: str | None,
    subtask_id: str | None,
    raw_value: str | None,
    store: PlanStore,
    normalize_value: Callable[[str | None], _FieldValue],
    replace_field: Callable[[Plan, str, _FieldValue], Plan],
    remaining: Remaining,
    saved_line: Callable[[Plan, str], str],
) -> ToolResult:
    """Chuẩn hóa ba đầu vào, sửa một việc con, chỉ ghi store khi plan đổi."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized_value = normalize_value(raw_value)
    plan = await _require_plan(store, normalized_plan_id, remaining)
    with _domain_as_tool_error():
        updated = replace_field(plan, normalized_subtask_id, normalized_value)
    if updated is not plan:
        await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, saved_line(updated, normalized_subtask_id))


def _day_text(day: date) -> str:
    """Ngày/tháng, mỗi phần hai chữ số, không năm."""

    return f"{day.day:02d}/{day.month:02d}"


def _load_sentence(days: list[tuple[date, DayLoad]], moves: tuple[ProposedMove, ...]) -> str:
    """Câu tool khi lần gọi đầu chưa ghi vì vượt. Không để core dựng câu."""

    clauses: list[str] = []
    for day, load in days:
        clause = f"Ngày {_day_text(day)} sẽ có {load.total} giờ trên quỹ {day_budget(day)} giờ"
        if load.provisional > 0:
            clause += f" (tính tạm: {load.provisional} việc chưa có sức, mỗi việc tính 3 giờ)"
        clauses.append(clause)
    text = "Lần này chưa ghi. " + ". ".join(clauses) + "."
    if not moves:
        return text
    pieces = [
        f"{index}. {move.title} (kế hoạch {move.goal}) sang {_day_text(move.scheduled_on)}."
        for index, move in enumerate(moves, start=1)
    ]
    return text + " Nếu vẫn ghi thì dời: " + " ".join(pieces)


def _partial_sentence(moved: list[str], waiting: list[str]) -> str:
    """Lần xin đã ghi, một lần dời sau đó lỗi."""

    return (
        "Đã ghi lần đang xin. "
        f"Đã dời: {', '.join(moved)}. "
        f"Chưa dời: {', '.join(waiting)}."
    )


def _watched(days: list[date | None], today: date) -> list[date]:
    """Ngày hôm nay hoặc ngày sau, mỗi ngày một lần, sớm trước."""

    return sorted({day for day in days if day is not None and day >= today})


def _parse_load_moves(raw: object) -> tuple[_Move, ...]:
    """Bỏ qua khi vắng. Sai kiểu là lỗi tool."""

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ToolError("Danh sách dời sai kiểu.")
    parsed: list[_Move] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ToolError("Danh sách dời sai kiểu.")
        plan_value = item.get("plan_id")
        task_value = item.get("subtask_id")
        if not isinstance(plan_value, str) or not isinstance(task_value, str):
            raise ToolError("Danh sách dời sai kiểu.")
        with _domain_as_tool_error():
            plan_id = normalize_plan_id(plan_value)
            task_id = normalize_subtask_id(task_value)
            day = normalize_scheduled_on(item.get("scheduled_on"))
        if day is None:
            raise ToolError("Ngày dời không được trống.")
        parsed.append((plan_id, task_id, day))
    return tuple(parsed)


def _check_moves(plans: tuple[Plan, ...], moves: tuple[_Move, ...]) -> None:
    """Mọi việc trong danh sách đã chốt còn và còn chưa làm. Sai thì không ghi."""

    by_id = {plan.id: plan for plan in plans}
    for plan_id, task_id, _day in moves:
        plan = by_id.get(plan_id)
        if plan is None:
            raise ToolError(_MOVE_GONE)
        task = next((item for item in plan.subtasks if item.id == task_id), None)
        if task is None or task.status is not SubtaskStatus.PENDING:
            raise ToolError(_MOVE_GONE)


def _overloads(
    plans: tuple[Plan, ...],
    today: date,
    days: list[date],
    incoming: tuple[tuple[str, str], ...],
) -> tuple[list[tuple[date, DayLoad]], tuple[ProposedMove, ...]]:
    """Các ngày vượt sau lần xin, và đoạn dời của từng ngày. Không ghi."""

    found: list[tuple[date, DayLoad]] = []
    chosen: list[ProposedMove] = []
    reserved: dict[date, int] = {}
    for day in days:
        load = day_load(plans, day, today)
        if load.total <= day_budget(day):
            continue
        found.append((day, load))
        moves = propose_load_moves(plans, day, today, incoming, reserved)
        chosen.extend(moves)
        for move in moves:
            source = next(item for item in plans if item.id == move.plan_id)
            task = next(item for item in source.subtasks if item.id == move.subtask_id)
            reserved[move.scheduled_on] = reserved.get(move.scheduled_on, 0) + task_hours(task)
    return found, tuple(chosen)


def _swap(plans: tuple[Plan, ...], updated: Plan) -> tuple[Plan, ...]:
    """Thay đúng kế hoạch trong bản đọc, giữ các kế hoạch khác."""

    return tuple(updated if plan.id == updated.id else plan for plan in plans)


def _with_date(plan: Plan, task_id: str, day: date) -> Plan:
    """Một việc sang ngày đã chốt. Các việc khác giữ nguyên."""

    subtasks = tuple(
        replace(item, scheduled_on=day) if item.id == task_id else item for item in plan.subtasks
    )
    return replace(plan, subtasks=subtasks)


def _task_title(plan: Plan, task_id: str) -> str:
    return next(item.title for item in plan.subtasks if item.id == task_id)


async def _read_plans(store: PlanStore, remaining: Remaining) -> tuple[Plan, ...]:
    """Một lần list_newest_first. Không đọc lại giữa hai lần ghi."""

    listed = await _await_store(remaining, store.list_newest_first, write=False)
    return listed


def _same_turn(turn: TurnContext | None, confirm: bool) -> None:
    """Cờ đã báo trong lượt này thì không ghi, dù là tải hay trùng hạn."""

    if turn is not None and confirm and turn.clash_reported:
        raise ToolError(_CONFIRM_SAME_TURN)


async def _write_moves(
    store: PlanStore,
    remaining: Remaining,
    turn: TurnContext,
    live: dict[str, Plan],
    moves: tuple[_Move, ...],
) -> None:
    """Ghi đúng mảng đã chốt. Lỗi sau lần xin thì dừng và báo phần đã dời."""

    titles = [_task_title(live[plan_id], task_id) for plan_id, task_id, _day in moves]
    moved: list[str] = []
    try:
        for index, (plan_id, task_id, day) in enumerate(moves):
            current = live[plan_id]
            sent = replace(current, subtasks=_with_date(current, task_id, day).subtasks)
            await _replace_plan(store, sent, remaining, moved_at=turn.instant)
            live[plan_id] = replace(sent, version=sent.version + 1)
            moved.append(titles[index])
    except Exception as error:
        raise ToolError(_partial_sentence(moved, titles[len(moved) :])) from error


async def _add_new_plan(
    store: PlanStore,
    remaining: Remaining,
    goal: str,
    subtasks: tuple[Subtask, ...],
    priority: Priority | None,
) -> Plan:
    """Ghi kế hoạch mới. Không ưu tiên thì add nhận đúng hai tham số vị trí."""

    if priority is None:
        call = lambda: store.add(goal, subtasks)
    else:
        call = lambda: store.add(goal, subtasks, priority=priority)
    return await _await_store(remaining, call, write=True)


async def create_plan(
    goal: str | None,
    subtasks: list[str] | list[object] | None = None,
    *,
    priority: str | None = None,
    confirm: bool = False,
    load_moves: list[object] | None = None,
    turn: TurnContext | None = None,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Lưu một kế hoạch đã chuẩn hóa. Không có turn thì không xét tải và không đoán mốc."""

    with _domain_as_tool_error():
        normalized_goal, normalized_subtasks = normalize_new_plan(goal, subtasks)
        normalized_priority = normalize_priority(priority)
    _same_turn(turn, confirm)
    today = None if turn is None else helsinki_clock(turn.instant)[0]
    watched = [] if today is None else _watched(
        [item.scheduled_on for item in normalized_subtasks],
        today,
    )
    if turn is None or today is None or not watched:
        plan = await _add_new_plan(
            store, remaining, normalized_goal, normalized_subtasks, normalized_priority
        )
        return _plan_tool_result(
            plan,
            saved_create(plan.goal, tuple(item.title for item in plan.subtasks)),
        )
    plans = await _read_plans(store, remaining)
    synthetic = Plan(
        id="mới",
        goal=normalized_goal,
        subtasks=normalized_subtasks,
        created_order=0,
        version=0,
        priority=normalized_priority,
    )
    incoming = tuple(("mới", item.id) for item in normalized_subtasks)
    if not confirm:
        found, moves = _overloads(plans + (synthetic,), today, watched, incoming)
        if found:
            turn.clash_reported = True
            return ToolResult(success=True, output=_load_sentence(found, moves))
        plan = await _add_new_plan(
            store, remaining, normalized_goal, normalized_subtasks, normalized_priority
        )
        return _plan_tool_result(
            plan,
            saved_create(plan.goal, tuple(item.title for item in plan.subtasks)),
        )
    parsed = _parse_load_moves(load_moves)
    _check_moves(plans, parsed)
    plan = await _add_new_plan(
        store, remaining, normalized_goal, normalized_subtasks, normalized_priority
    )
    live = {item.id: item for item in plans}
    await _write_moves(store, remaining, turn, live, parsed)
    return _plan_tool_result(
        plan,
        saved_create(plan.goal, tuple(item.title for item in plan.subtasks)),
    )


def _plans_json(plans: tuple[Plan, ...]) -> str:
    """Đổi danh sách Plan sang JSON. created_order không có trong JSON."""

    body = PlansJson(plans=[_plan_json(plan) for plan in plans])
    return body.model_dump_json(ensure_ascii=False)


async def get_plans(
    keyword: str | None = None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Liệt kê kế hoạch mới hơn đứng trước, rồi lọc theo từ khóa trong goal hoặc tiêu đề việc con."""

    plans = await _await_store(remaining, store.list_newest_first, write=False)
    listed = filter_by_keyword(plans, keyword)
    return ToolResult(success=True, output=_plans_json(listed))


async def get_plan_detail(
    plan_id: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Mở một kế hoạch theo danh tính đã lưu, hoặc ném ToolError."""

    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
    plan = await _require_plan(store, normalized_id, remaining)
    return _plan_tool_result(plan)


async def update_subtask(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt trạng thái một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return await _replace_subtask_field(
        plan_id,
        subtask_id,
        status,
        store,
        normalize_subtask_status,
        replace_subtask_status,
        remaining,
        _status_saved_line,
    )


async def add_subtask(
    plan_id: str | None,
    title: str | None,
    *,
    scheduled_on: str | None = None,
    effort: str | None = None,
    confirm: bool = False,
    load_moves: list[object] | None = None,
    turn: TurnContext | None = None,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Thêm một việc con vào cuối. Không kiểm trùng hạn. Không có turn thì không xét tải."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        subtask = replace(
            new_subtask(title),
            scheduled_on=normalize_scheduled_on(scheduled_on),
            effort=normalize_effort(effort),
        )
    _same_turn(turn, confirm)
    today = None if turn is None else helsinki_clock(turn.instant)[0]
    watched = [] if today is None else _watched([subtask.scheduled_on], today)
    parsed = _parse_load_moves(load_moves) if confirm else ()
    if turn is None or today is None or (not watched and not parsed):
        stored = await _require_plan(store, normalized_plan_id, remaining)
        updated = append_subtask(stored, subtask)
        await _replace_plan(store, updated, remaining)
        added = updated.subtasks[-1]
        return _plan_tool_result(updated, saved_add(added.title, updated.goal))
    plans = await _read_plans(store, remaining)
    stored = next((plan for plan in plans if plan.id == normalized_plan_id), None)
    if stored is None:
        raise ToolError(_MISSING_PLAN_MESSAGE)
    updated = append_subtask(stored, subtask)
    incoming = ((updated.id, subtask.id),)
    if not confirm:
        found, moves = _overloads(_swap(plans, updated), today, watched, incoming)
        if found:
            turn.clash_reported = True
            return ToolResult(success=True, output=_load_sentence(found, moves))
        await _replace_plan(store, updated, remaining)
        added = updated.subtasks[-1]
        return _plan_tool_result(updated, saved_add(added.title, updated.goal))
    _check_moves(plans, parsed)
    live = {plan.id: plan for plan in plans}
    sent = replace(live[updated.id], subtasks=updated.subtasks)
    await _replace_plan(store, sent, remaining)
    live[updated.id] = replace(sent, version=sent.version + 1)
    await _write_moves(store, remaining, turn, live, parsed)
    added = live[updated.id].subtasks[-1]
    return _plan_tool_result(live[updated.id], saved_add(added.title, updated.goal))


async def set_subtask_note(
    plan_id: str | None,
    subtask_id: str | None,
    note: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt ghi chú một việc con, hoặc ném ToolError với đúng câu đầu tiên."""

    return await _replace_subtask_field(
        plan_id,
        subtask_id,
        note,
        store,
        normalize_subtask_note,
        replace_subtask_note,
        remaining,
        _note_saved_line,
    )


def _priority_line(plan: Plan) -> str:
    if plan.priority is None:
        return saved_clear_priority(plan.goal)
    return saved_set_priority(_PRIORITY_LABEL[plan.priority], plan.goal)


async def set_plan_priority(
    plan_id: str | None,
    priority: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt hoặc xóa ưu tiên. Không đụng ngày, sức, hay lịch sử."""

    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
        normalized = normalize_priority(priority)
    plan = await _require_plan(store, normalized_id, remaining)
    if plan.priority == normalized:
        return _plan_tool_result(plan, _priority_line(plan))
    updated = replace(plan, priority=normalized)
    await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, _priority_line(updated))


async def set_subtask_effort(
    plan_id: str | None,
    subtask_id: str | None,
    effort: str | None,
    *,
    store: PlanStore,
    remaining: Remaining = None,
) -> ToolResult:
    """Đặt hoặc xóa sức của một việc. Không đụng ưu tiên hay ngày."""

    with _domain_as_tool_error():
        normalized_plan_id = normalize_plan_id(plan_id)
        normalized_subtask_id = normalize_subtask_id(subtask_id)
        normalized = normalize_effort(effort)
    plan = await _require_plan(store, normalized_plan_id, remaining)
    current = next((item for item in plan.subtasks if item.id == normalized_subtask_id), None)
    if current is None:
        raise PlanDomainError(_MISSING_SUBTASK)
    if current.effort == normalized:
        return _plan_tool_result(
            plan,
            _effort_line(plan, normalized_subtask_id),
        )
    updated_items = tuple(
        replace(item, effort=normalized) if item.id == normalized_subtask_id else item
        for item in plan.subtasks
    )
    updated = replace(plan, subtasks=updated_items)
    await _replace_plan(store, updated, remaining)
    return _plan_tool_result(updated, _effort_line(updated, normalized_subtask_id))


def _effort_line(plan: Plan, subtask_id: str) -> str:
    item = next(subtask for subtask in plan.subtasks if subtask.id == subtask_id)
    if item.effort is None:
        return saved_clear_effort(item.title, plan.goal)
    return saved_set_effort(item.effort.value, item.title, plan.goal)


def _clash_text(other: Plan) -> str:
    deadline = plan_deadline(other)
    if deadline is None:
        raise PlanDomainError("Kế hoạch kia không có hạn.")
    day = deadline.isoformat()
    return (
        f"Lần này chưa ghi. Kế hoạch {other.goal} cũng đến hạn {day}. "
        "Hỏi chủ bot, rồi chỉ gọi lại với confirm ở lượt sau."
    )


def _apply_changes(plan: Plan, changes: list[object]) -> tuple[Plan, tuple[str, ...]]:
    """Dựng kế hoạch sau lần dời. Không ghi. Lỗi miền thì không có bản mới."""

    if not changes:
        raise PlanDomainError(_EMPTY_CHANGES)
    by_id = {item.id: item for item in plan.subtasks}
    seen: set[str] = set()
    updated = dict(by_id)
    titles: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            raise PlanDomainError(_DUPLICATE_CHANGE)
        subtask_id = change.get("subtask_id")
        if not isinstance(subtask_id, str):
            raise PlanDomainError(_MISSING_SUBTASK)
        if subtask_id in seen:
            raise PlanDomainError(_DUPLICATE_CHANGE)
        seen.add(subtask_id)
        if subtask_id not in by_id:
            raise PlanDomainError(_MISSING_SUBTASK)
        scheduled_on = normalize_scheduled_on(change.get("scheduled_on"))
        current = by_id[subtask_id]
        if current.scheduled_on == scheduled_on:
            continue
        titles.append(current.title)
        updated[subtask_id] = replace(current, scheduled_on=scheduled_on)
    subtasks = tuple(updated[item.id] for item in plan.subtasks)
    return replace(plan, subtasks=subtasks), tuple(titles)


async def reschedule_subtasks(
    plan_id: str | None,
    changes: list[object] | None,
    *,
    reason: str | None = None,
    confirm: bool = False,
    load_moves: list[object] | None = None,
    store: PlanStore,
    remaining: Remaining = None,
    turn: TurnContext | None = None,
) -> ToolResult:
    """Dời ngày. Không có ngữ cảnh thì không ghi và không đọc đồng hồ."""

    if turn is None:
        raise ToolError(_NEED_TURN)
    if changes is None:
        raise PlanDomainError(_EMPTY_CHANGES)
    _same_turn(turn, confirm)
    with _domain_as_tool_error():
        normalized_id = normalize_plan_id(plan_id)
        normalized_reason = normalize_move_reason(reason)
        requested = [
            normalize_scheduled_on(change.get("scheduled_on"))
            if isinstance(change, dict)
            else None
            for change in changes
        ]
    today = helsinki_clock(turn.instant)[0]
    mentioned = _watched(requested, today)
    parsed = _parse_load_moves(load_moves) if confirm else ()
    listed = False
    if mentioned or parsed:
        plans = await _read_plans(store, remaining)
        listed = True
        plan = next((item for item in plans if item.id == normalized_id), None)
        if plan is None:
            raise ToolError(_MISSING_PLAN_MESSAGE)
    else:
        plans = ()
        plan = await _require_plan(store, normalized_id, remaining)
    updated, titles = _apply_changes(plan, changes)
    if not titles:
        return _plan_tool_result(plan)
    incoming = tuple(
        (plan.id, new.id)
        for old, new in zip(plan.subtasks, updated.subtasks, strict=True)
        if old.scheduled_on != new.scheduled_on
        and new.scheduled_on is not None
        and new.scheduled_on >= today
    )
    watched = _watched(
        [
            new.scheduled_on
            for old, new in zip(plan.subtasks, updated.subtasks, strict=True)
            if (plan.id, new.id) in incoming
        ],
        today,
    )
    other: Plan | None = None
    if not confirm:
        found: list[tuple[date, DayLoad]] = []
        moves: tuple[ProposedMove, ...] = ()
        if watched:
            found, moves = _overloads(_swap(plans, updated), today, watched, incoming)
        if plan_deadline(plan) != plan_deadline(updated):
            others = plans if listed else await _read_plans(store, remaining)
            other = deadline_clash(updated, others)
        if found or other is not None:
            turn.clash_reported = True
            if found and other is not None:
                text = _load_sentence(found, moves)
                deadline = plan_deadline(other)
                if deadline is None:
                    raise PlanDomainError("Kế hoạch kia không có hạn.")
                text += f" Kế hoạch {other.goal} cũng đến hạn {deadline.isoformat()}."
                return ToolResult(success=True, output=text)
            if found:
                return ToolResult(success=True, output=_load_sentence(found, moves))
            return ToolResult(success=True, output=_clash_text(other))
    if parsed:
        if not plans:
            plans = await _read_plans(store, remaining)
        _check_moves(plans, parsed)
    live = {item.id: item for item in plans} if plans else {plan.id: plan}
    if plan.id not in live:
        live[plan.id] = plan
    sent = replace(live[plan.id], subtasks=updated.subtasks)
    await _replace_plan(
        store,
        sent,
        remaining,
        move_reason=normalized_reason,
        moved_at=turn.instant,
    )
    live[plan.id] = replace(sent, version=sent.version + 1)
    await _write_moves(store, remaining, turn, live, parsed)
    return _plan_tool_result(live[plan.id], saved_reschedule(titles, updated.goal))
