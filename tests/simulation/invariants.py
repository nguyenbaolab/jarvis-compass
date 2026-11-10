"""Mười bất biến của mô phỏng ngẫu nhiên. Vi phạm thì in hạt giống, ngày, hành động, ảnh chụp."""

from datetime import date

from core.morning import render_digest
from core.plans import day_budget, day_load
from core.telegram_channel import split_utf16

from tests.simulation.harness import MorningSend, format_fingerprint


class InvariantViolation(AssertionError):
    """Mã trong src/ làm lệch một bất biến. Không nới điều kiện để qua."""


def violate(
    seed: int,
    day: date,
    action: str,
    before: tuple[object, ...],
    after: tuple[object, ...],
    message: str,
) -> None:
    text = "\n".join(
        (
            f"seed={seed}",
            f"day={day.isoformat()}",
            f"action={action}",
            message,
            "before:",
            format_fingerprint(before),
            "after:",
            format_fingerprint(after),
        )
    )
    raise InvariantViolation(text)


def check_morning(
    *,
    seed: int,
    day: date,
    send: MorningSend,
    plans: tuple[object, ...],
    before: tuple[object, ...],
    after: tuple[object, ...],
) -> None:
    """Tin sáng bằng render_digest lúc gửi, đúng một lần, và không tự dời việc."""

    digest = render_digest(plans)
    parts = len(split_utf16(digest))
    if send.text != digest or send.parts != parts or send.parts < 1:
        violate(
            seed,
            day,
            "run_morning",
            before,
            after,
            f"(vii) tin sáng lệch render_digest hoặc không đúng một lần. "
            f"parts={send.parts} expected_parts={parts}",
        )
    if before != after:
        violate(seed, day, "run_morning", before, after, "(viii) tin sáng làm đổi kho.")


def check_action(
    *,
    seed: int,
    day: date,
    action: str,
    before: tuple[object, ...],
    after: tuple[object, ...],
    output: str,
    success: bool,
    confirmed: bool,
    targeted_status: set[tuple[str, str]],
    targeted_dates: set[tuple[str, str]],
    today: date,
    succeeded: dict[str, int],
    history: int,
    known_pairs: set[tuple[str, str]],
    versions: dict[str, int],
    tool_name: str = "",
    request: dict[str, object] | None = None,
) -> None:
    """Kiểm sau một lời gọi tool. Cảnh báo là lần gọi có câu chưa ghi."""

    warned = success and "Lần này chưa ghi." in output
    if warned and before != after:
        violate(seed, day, action, before, after, "(i) lần gọi đầu bị cảnh báo nhưng kho đổi.")
    _check_pairs(seed, day, action, before, after, known_pairs)
    _check_versions(seed, day, action, before, after, succeeded, versions)
    _check_history(seed, day, action, before, after, history)
    if success and not warned and not confirmed:
        _check_budget(seed, day, action, before, after, today)
    _check_fields(
        seed,
        day,
        action,
        before,
        after,
        targeted_status,
        targeted_dates,
        today,
    )
    if confirmed and success and not warned and request is not None:
        _check_applied(seed, day, action, before, after, tool_name, request)


def _plans(shot: tuple[object, ...]):
    return shot[0]


def _moves(shot: tuple[object, ...]):
    return shot[1]


def _check_pairs(seed, day, action, before, after, known_pairs: set[tuple[str, str]]) -> None:
    current = _pair_set(after)
    missing = known_pairs - current
    if missing:
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"(ii) cặp kế hoạch-việc biến mất: {sorted(missing)}",
        )
    known_pairs.clear()
    known_pairs.update(current)


def _pair_set(shot: tuple[object, ...]) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for plan in _plans(shot):
        for task in plan[5]:
            found.add((plan[0], task[0]))
    return found


def _check_versions(seed, day, action, before, after, succeeded, versions: dict[str, int]) -> None:
    for plan in _plans(after):
        plan_id = plan[0]
        version = plan[3]
        expected = succeeded.get(plan_id, 0)
        if version != expected:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(iii) version của {plan[1]!r} là {version}, số replace thành công là {expected}.",
            )
        previous = versions.get(plan_id)
        if previous is not None and version < previous:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(iii) version của {plan[1]!r} giảm từ {previous} xuống {version}.",
            )
        versions[plan_id] = version


def _check_history(seed, day, action, before, after, history: int) -> None:
    if len(_moves(after)) != history:
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"(iv) lịch sử có {len(_moves(after))} dòng, số việc đổi ngày-sang-ngày là {history}.",
        )


def _check_budget(seed, day, action, before, after, today: date) -> None:
    placed = _placed_days(before, after, today)
    plans = _plan_objects_from_fingerprint(after)
    for placed_day in sorted(placed):
        load = day_load(plans, placed_day, today)
        budget = day_budget(placed_day)
        if load.total > budget:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(v) ngày {placed_day.isoformat()} tải {load.total} giờ, quỹ {budget}.",
            )


def _placed_days(before, after, today: date) -> set[date]:
    """Ngày từ hôm nay trở đi mà lời gọi đặt việc lên, kể cả việc mới."""

    old_days = _task_days(before)
    new_days = _task_days(after)
    placed: set[date] = set()
    for key, new_day in new_days.items():
        if new_day is None:
            continue
        if new_day < today:
            continue
        if key not in old_days or old_days[key] != new_day:
            placed.add(new_day)
    return placed


def _task_days(shot) -> dict[tuple[str, str], date | None]:
    found: dict[tuple[str, str], date | None] = {}
    for plan in _plans(shot):
        for task in plan[5]:
            raw = task[4]
            found[(plan[0], task[0])] = None if raw is None else date.fromisoformat(raw)
    return found


def _plan_objects_from_fingerprint(shot):
    """Dựng Plan tối thiểu để day_load đọc status, ngày và sức."""

    from core.plans import Effort, Plan, Priority, Subtask, SubtaskStatus

    built: list[Plan] = []
    for plan_id, goal, created_order, version, priority, tasks in _plans(shot):
        subtasks = tuple(
            Subtask(
                id=task_id,
                title=title,
                status=SubtaskStatus(status),
                note=note,
                scheduled_on=None if raw_day is None else date.fromisoformat(raw_day),
                effort=None if effort is None else Effort(effort),
            )
            for task_id, title, status, note, raw_day, effort in tasks
        )
        built.append(
            Plan(
                id=plan_id,
                goal=goal,
                subtasks=subtasks,
                created_order=created_order,
                version=version,
                priority=None if priority is None else Priority(priority),
            )
        )
    return tuple(built)


def _check_fields(
    seed,
    day,
    action,
    before,
    after,
    targeted_status: set[tuple[str, str]],
    targeted_dates: set[tuple[str, str]],
    today: date,
) -> None:
    old = _task_map(before)
    new = _task_map(after)
    for key, previous in old.items():
        if key not in new:
            continue
        current = new[key]
        if current[0] != previous[0] or current[2] != previous[2]:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(vi) tiêu đề hoặc ghi chú đổi ngoài hành động: {previous[0]!r}.",
            )
        if current[1] != previous[1] and key not in targeted_status:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(vi) trạng thái của {previous[0]!r} đổi ngoài update_subtask.",
            )
        if current[3] == previous[3] or key in targeted_dates:
            continue
        if previous[3] is not None and date.fromisoformat(previous[3]) < today:
            violate(
                seed,
                day,
                action,
                before,
                after,
                "(viii) việc quá hạn "
                f"{previous[0]!r} bị dời từ {previous[3]} sang {current[3]}, ngoài danh sách (ix).",
            )
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"(ix) việc {previous[0]!r} đổi ngày từ {previous[3]} sang {current[3]} ngoài danh sách.",
        )


def _check_applied(
    seed: int,
    day: date,
    action: str,
    before: tuple[object, ...],
    after: tuple[object, ...],
    tool_name: str,
    request: dict[str, object],
) -> None:
    """Xác nhận thành công thì mọi việc dời tới đúng ngày, và lần xin có mặt trong kho."""

    moves = request.get("load_moves")
    if isinstance(moves, list):
        for move in moves:
            if not isinstance(move, dict):
                violate(seed, day, action, before, after, "(x) danh sách dời không phải object.")
            plan_id = str(move.get("plan_id"))
            task_id = str(move.get("subtask_id"))
            expected = move.get("scheduled_on")
            actual = _scheduled(after, plan_id, task_id)
            if actual != expected:
                violate(
                    seed,
                    day,
                    action,
                    before,
                    after,
                    f"(x) việc {task_id} còn ngày {actual}, đích xác nhận là {expected}.",
                )
    if tool_name == "add_subtask":
        _expect_added(seed, day, action, before, after, request)
    elif tool_name == "create_plan":
        _expect_created(seed, day, action, before, after, request)
    elif tool_name == "reschedule_subtasks":
        _expect_rescheduled(seed, day, action, before, after, request)


def _scheduled(shot: tuple[object, ...], plan_id: str, task_id: str) -> str | None:
    for plan in _plans(shot):
        if plan[0] != plan_id:
            continue
        for task in plan[5]:
            if task[0] == task_id:
                return task[4]
    return None


def _expect_added(seed, day, action, before, after, request: dict[str, object]) -> None:
    title = request.get("title")
    expected = request.get("scheduled_on") if "scheduled_on" in request else None
    old_ids = _pair_set(before)
    found = [
        task
        for plan in _plans(after)
        for task in plan[5]
        if (plan[0], task[0]) not in old_ids and task[1] == title
    ]
    if len(found) != 1 or found[0][4] != expected:
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"(x) việc xin {title!r} ngày {expected} không có trong kho.",
        )


def _expect_created(seed, day, action, before, after, request: dict[str, object]) -> None:
    goal = request.get("goal")
    old_ids = {plan[0] for plan in _plans(before)}
    created = [plan for plan in _plans(after) if plan[0] not in old_ids and plan[1] == goal]
    raw = request.get("subtasks")
    wanted = raw if isinstance(raw, list) else []
    if len(created) != 1:
        violate(seed, day, action, before, after, f"(x) không thấy kế hoạch mới {goal!r}.")
    tasks = created[0][5]
    if len(tasks) != len(wanted):
        violate(seed, day, action, before, after, f"(x) kế hoạch {goal!r} không đủ việc xin.")
    for task, item in zip(tasks, wanted, strict=True):
        if not isinstance(item, dict):
            violate(seed, day, action, before, after, "(x) việc xin không phải object.")
        expected = item.get("scheduled_on") if "scheduled_on" in item else None
        if task[1] != item.get("title") or task[4] != expected:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(x) việc {item.get('title')!r} không đúng tiêu đề hoặc ngày.",
            )


def _expect_rescheduled(seed, day, action, before, after, request: dict[str, object]) -> None:
    plan_id = str(request.get("plan_id"))
    changes = request.get("changes")
    if not isinstance(changes, list):
        violate(seed, day, action, before, after, "(x) lần dời không có changes.")
    for change in changes:
        if not isinstance(change, dict):
            violate(seed, day, action, before, after, "(x) một việc dời không phải object.")
        task_id = str(change.get("subtask_id"))
        expected = change.get("scheduled_on")
        before_day = _scheduled(before, plan_id, task_id)
        actual = _scheduled(after, plan_id, task_id)
        if before_day == expected:
            continue
        if actual != expected:
            violate(
                seed,
                day,
                action,
                before,
                after,
                f"(x) việc {task_id} chưa đổi sang {expected}, đang là {actual}.",
            )


def _task_map(shot) -> dict[tuple[str, str], tuple[str, str, str | None, str | None]]:
    """title, status, note, day iso."""

    found: dict[tuple[str, str], tuple[str, str, str | None, str | None]] = {}
    for plan in _plans(shot):
        for task in plan[5]:
            found[(plan[0], task[0])] = (task[1], task[2], task[3], task[4])
    return found
