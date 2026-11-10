"""Mô phỏng 30 ngày với random.Random(seed). Một phần hạt ném lỗi replace."""

import random
import re
from collections import Counter
from datetime import date, timedelta

from core.clock import helsinki_clock

from tests.simulation.harness import (
    BotOwner,
    CountingStore,
    DayClock,
    MemoryPlanStore,
    World,
    fingerprint,
    forecast_add,
    forecast_create,
    forecast_reschedule,
    moves_payload,
    sentence_move_count,
)
from tests.simulation.invariants import check_action, check_morning, violate

PLAIN_SEEDS = (11, 29, 47)
NTH_SEEDS = (83,)
TARGETED_SEEDS = (97, 131)
ALL_SEEDS = PLAIN_SEEDS + NTH_SEEDS + TARGETED_SEEDS
DAYS = 30
_START = date(2026, 11, 16)
_COUNT_KEYS = (
    "actions",
    "warnings_load",
    "warnings_clash",
    "confirmed_ok",
    "declined",
    "partial_sentences",
    "moves_applied",
    "morning_sends",
)
_PARTIAL = re.compile(r"^Đã ghi lần đang xin\. Đã dời: (.*?)\. Chưa dời: (.*?)\.$", re.DOTALL)


def empty_counts() -> Counter:
    return Counter({key: 0 for key in _COUNT_KEYS})


def _mode(seed: int) -> str:
    if seed in NTH_SEEDS:
        return "nth"
    if seed in TARGETED_SEEDS:
        return "second"
    return "plain"


async def run_seed(seed: int) -> Counter:
    """Một hạt, 30 ngày, 0 đến 4 hành động mỗi ngày. Trả bộ đếm độ phủ."""

    rng = random.Random(seed)
    mode = _mode(seed)
    fail_at = rng.randint(3, 10) if mode == "nth" else None
    store = CountingStore(MemoryPlanStore(), fail_at)
    world = World(store)
    owner = BotOwner(store)
    known_pairs: set[tuple[str, str]] = set()
    versions: dict[str, int] = {}
    counts = empty_counts()
    serial = 0
    for offset in range(DAYS):
        day = _START + timedelta(days=offset)
        instant = world_morning(day)
        before = await fingerprint(store)
        send = await world.morning(instant)
        plans = await store.list_newest_first()
        after = await fingerprint(store)
        check_morning(
            seed=seed,
            day=day,
            send=send,
            plans=plans,
            before=before,
            after=after,
        )
        counts["morning_sends"] += 1
        count = rng.randint(0, 4)
        clock = DayClock(day)
        for _index in range(count):
            serial = await _one_action(
                rng,
                owner,
                store,
                day,
                clock,
                seed,
                serial,
                known_pairs,
                versions,
                counts,
                mode == "second",
            )
    if mode == "nth" and store.failures != 1:
        raise AssertionError(
            f"seed={seed} fail_at={fail_at} attempts={store.attempts} failures={store.failures}"
        )
    if mode == "second" and store.failures < 1:
        raise AssertionError(
            f"seed={seed} chế độ nhắm replace thứ hai không ném. failures={store.failures}"
        )
    return counts


def world_morning(day: date):
    from tests.simulation.harness import at_helsinki

    return at_helsinki(day, 8, 0)


async def _one_action(
    rng, owner, store, day, clock, seed, serial, known_pairs, versions, counts, targeted: bool
) -> int:
    instant = clock.next()
    catalog = await owner.catalog(instant)
    plans = await store.list_newest_first()
    kind = _pick(rng, plans)
    serial, name, payload, label, status_ids, date_ids = _build(
        rng, catalog, kind, serial, day
    )
    await _call(
        rng,
        owner,
        store,
        day,
        seed,
        name,
        payload,
        label,
        status_ids,
        date_ids,
        instant,
        clock,
        known_pairs,
        versions,
        counts,
        targeted,
        confirmed=False,
    )
    return serial


def _pick(rng: random.Random, plans: tuple[object, ...]) -> str:
    options = ["create_plan", "create_plan"]
    if plans:
        options.extend(["add_subtask", "add_subtask", "add_subtask"])
        if any(plan.subtasks for plan in plans):
            options.extend(["reschedule_subtasks", "reschedule_subtasks", "update_subtask"])
    return rng.choice(options)


def _build(rng, catalog, kind: str, serial: int, today: date):
    if kind == "create_plan":
        serial += 1
        goal = f"Kế hoạch {serial}"
        count = rng.randint(1, 3)
        subtasks = []
        for _item in range(count):
            serial += 1
            task: dict[str, object] = {"title": f"Việc {serial}"}
            scheduled = _maybe_day(rng, today)
            effort = _maybe_effort(rng)
            if scheduled is not None:
                task["scheduled_on"] = scheduled
            if effort is not None:
                task["effort"] = effort
            subtasks.append(task)
        payload: dict[str, object] = {"goal": goal, "subtasks": subtasks}
        priority = rng.choice((None, "high", "medium", "low"))
        if priority is not None:
            payload["priority"] = priority
        label = f"create_plan {goal} priority={priority} tasks={_titles(subtasks)}"
        return serial, "create_plan", payload, label, set(), set()
    plan = rng.choice(catalog)
    if kind == "add_subtask":
        serial += 1
        title = f"Việc {serial}"
        payload = {"plan_id": plan["id"], "title": title}
        scheduled = _maybe_day(rng, today)
        effort = _maybe_effort(rng)
        if scheduled is not None:
            payload["scheduled_on"] = scheduled
        if effort is not None:
            payload["effort"] = effort
        label = (
            f"add_subtask {title} plan={plan['goal']} day={scheduled} effort={effort}"
        )
        return serial, "add_subtask", payload, label, set(), set()
    tasks = plan["subtasks"]
    task = rng.choice(tasks)
    if kind == "update_subtask":
        status = rng.choice(("pending", "done", "skipped"))
        payload = {
            "plan_id": plan["id"],
            "subtask_id": task["id"],
            "status": status,
        }
        label = f"update_subtask {task['title']} plan={plan['goal']} status={status}"
        return serial, "update_subtask", payload, label, {(plan["id"], task["id"])}, set()
    scheduled = _maybe_day(rng, today)
    payload = {
        "plan_id": plan["id"],
        "changes": [{"subtask_id": task["id"], "scheduled_on": scheduled}],
    }
    label = f"reschedule_subtasks {task['title']} plan={plan['goal']} day={scheduled}"
    return serial, "reschedule_subtasks", payload, label, set(), {(plan["id"], task["id"])}


def _titles(subtasks: list[dict[str, object]]) -> str:
    return ",".join(str(item["title"]) for item in subtasks)


def _maybe_day(rng: random.Random, today: date) -> str | None:
    roll = rng.randrange(8)
    if roll == 0:
        return None
    if roll == 1:
        return (today - timedelta(days=rng.randint(1, 3))).isoformat()
    return (today + timedelta(days=rng.randint(0, 3))).isoformat()


def _maybe_effort(rng: random.Random) -> str | None:
    return rng.choice(("M", "L", "L", "M", "L", None, "S"))


async def _call(
    rng,
    owner,
    store,
    day,
    seed,
    name,
    payload,
    label,
    status_ids,
    date_ids,
    instant,
    clock,
    known_pairs,
    versions,
    counts: Counter,
    targeted: bool,
    *,
    confirmed: bool,
) -> None:
    moves = payload.get("load_moves")
    move_list = moves if isinstance(moves, list) else []
    fail_second = confirmed and targeted and len(move_list) >= 1
    store.prepare_call(fail_second_replace=fail_second)
    before = await fingerprint(store)
    failures_before = store.failures
    result = await owner.tool(name, payload, instant)
    if store.failures > failures_before and result.success:
        raise AssertionError(
            f"seed={seed} day={day.isoformat()} action={label} "
            "replace ném lỗi nhưng tool báo thành công."
        )
    after = await fingerprint(store)
    today = helsinki_clock(instant)[0]
    counts["actions"] += 1
    check_action(
        seed=seed,
        day=day,
        action=label,
        before=before,
        after=after,
        output=result.output,
        success=result.success,
        confirmed=confirmed,
        targeted_status=status_ids,
        targeted_dates=date_ids,
        today=today,
        succeeded=store.succeeded,
        history=store.history,
        known_pairs=known_pairs,
        versions=versions,
        tool_name=name,
        request=payload if confirmed else None,
    )
    if fail_second and store.failures > failures_before:
        _check_targeted_failure(
            seed,
            day,
            label,
            before,
            after,
            result.output,
            move_list,
            name,
            payload,
        )
    if confirmed:
        counts["moves_applied"] += _applied_moves(before, after, move_list)
        if result.output.startswith("Đã ghi lần đang xin"):
            counts["partial_sentences"] += 1
        elif result.success and "Lần này chưa ghi." not in result.output:
            counts["confirmed_ok"] += 1
        return
    warned = result.success and "Lần này chưa ghi." in result.output
    if not warned:
        return
    overload = "trên quỹ" in result.output
    if overload:
        counts["warnings_load"] += 1
    elif "cũng đến hạn" in result.output:
        counts["warnings_clash"] += 1
        counts["declined"] += 1
        return
    else:
        counts["declined"] += 1
        return
    forecast = await _forecast(store, name, payload, today)
    if sentence_move_count(result.output) != len(forecast):
        raise RuntimeError(
            "Danh sách dời lệch propose_load_moves.\n"
            f"seed={seed} day={day.isoformat()} action={label}\n"
            f"tool={result.output}\n"
            f"forecast={[(move.goal, move.title, move.scheduled_on.isoformat()) for move in forecast]}"
        )
    if rng.random() >= 0.6:
        counts["declined"] += 1
        return
    confirm_payload = dict(payload)
    confirm_payload["confirm"] = True
    confirm_payload["load_moves"] = moves_payload(forecast)
    confirm_dates = set(date_ids)
    for move in forecast:
        confirm_dates.add((move.plan_id, move.subtask_id))
    await _call(
        rng,
        owner,
        store,
        day,
        seed,
        name,
        confirm_payload,
        label + " confirm",
        status_ids,
        confirm_dates,
        clock.next(),
        clock,
        known_pairs,
        versions,
        counts,
        targeted,
        confirmed=True,
    )


def _applied_moves(before, after, moves: list[object]) -> int:
    applied = 0
    for move in moves:
        if not isinstance(move, dict):
            continue
        plan_id = str(move.get("plan_id"))
        task_id = str(move.get("subtask_id"))
        old = _scheduled(before, plan_id, task_id)
        new = _scheduled(after, plan_id, task_id)
        if old != new and new == move.get("scheduled_on"):
            applied += 1
    return applied


def _scheduled(shot, plan_id: str, task_id: str) -> str | None:
    for plan in shot[0]:
        if plan[0] != plan_id:
            continue
        for task in plan[5]:
            if task[0] == task_id:
                return task[4]
    return None


def _check_targeted_failure(
    seed,
    day,
    action,
    before,
    after,
    output: str,
    moves: list[object],
    name: str,
    payload: dict[str, object],
) -> None:
    """Việc đổi ngày bằng hợp của Đã dời và việc lần xin nhắm tới. Chưa dời là phần còn lại."""

    matched = _PARTIAL.match(output)
    if matched is None or not output.startswith("Đã ghi lần đang xin."):
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"Lời replace thứ hai không bắt đầu bằng câu đã ghi: {output}",
        )
        return
    moved = _split_titles(matched.group(1))
    waiting = _split_titles(matched.group(2))
    changed = set(_changed_titles(before, after))
    reported = set(moved)
    requested = _request_date_titles(name, payload, before)
    unchanged = reported - changed
    if unchanged:
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"Đã dời có việc ngày không đổi: {sorted(unchanged)}.",
        )
        return
    union = reported | requested
    if changed != union:
        violate(
            seed,
            day,
            action,
            before,
            after,
            "Tập việc đổi ngày "
            f"{sorted(changed)} không bằng hợp của Đã dời {sorted(reported)} "
            f"và lần xin {sorted(requested)}.",
        )
        return
    move_titles = [_move_title(before, move) for move in moves]
    rest = _without_reported(move_titles, moved)
    if waiting != rest:
        violate(
            seed,
            day,
            action,
            before,
            after,
            f"Chưa dời {waiting} không bằng load_moves trừ Đã dời, còn {rest}.",
        )


def _split_titles(text: str) -> list[str]:
    stripped = text.strip()
    if stripped == "":
        return []
    return [part.strip() for part in stripped.split(", ") if part.strip() != ""]


def _changed_titles(before, after) -> list[str]:
    new = _scheduled_map(after)
    titles: list[str] = []
    for plan in sorted(before[0], key=lambda item: item[2]):
        for task in plan[5]:
            key = (plan[0], task[0])
            if key in new and new[key] != task[4]:
                titles.append(task[1])
    return titles


def _scheduled_map(shot) -> dict[tuple[str, str], str | None]:
    found: dict[tuple[str, str], str | None] = {}
    for plan in shot[0]:
        for task in plan[5]:
            found[(plan[0], task[0])] = task[4]
    return found


def _move_title(before, move: object) -> str:
    if not isinstance(move, dict):
        return ""
    plan_id = str(move.get("plan_id"))
    task_id = str(move.get("subtask_id"))
    for plan in before[0]:
        if plan[0] != plan_id:
            continue
        for task in plan[5]:
            if task[0] == task_id:
                return task[1]
    return ""


def _request_date_titles(name: str, payload: dict[str, object], before) -> set[str]:
    """Việc lần xin làm đổi ngày. Thêm việc và tạo kế hoạch không đổi ngày việc cũ."""

    if name != "reschedule_subtasks":
        return set()
    plan_id = str(payload.get("plan_id"))
    changes = payload.get("changes")
    if not isinstance(changes, list):
        return set()
    titles: set[str] = set()
    for change in changes:
        if not isinstance(change, dict):
            continue
        task_id = change.get("subtask_id")
        if not isinstance(task_id, str):
            continue
        if _scheduled(before, plan_id, task_id) == _as_day(change.get("scheduled_on")):
            continue
        title = _title(before, plan_id, task_id)
        titles.add(task_id if title is None else title)
    return titles


def _as_day(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _title(shot, plan_id: str, task_id: str) -> str | None:
    for plan in shot[0]:
        if plan[0] != plan_id:
            continue
        for task in plan[5]:
            if task[0] == task_id:
                return task[1]
    return None


def _without_reported(move_titles: list[str], moved: list[str]) -> list[str]:
    """load_moves theo thứ tự, bỏ từng tiêu đề đã báo Đã dời một lần."""

    pending = Counter(moved)
    rest: list[str] = []
    for title in move_titles:
        if pending[title] > 0:
            pending[title] -= 1
            continue
        rest.append(title)
    return rest


async def _forecast(store, name: str, payload: dict[str, object], today: date):
    if name == "create_plan":
        return await forecast_create(
            store,
            str(payload["goal"]),
            payload.get("subtasks"),
            payload.get("priority") if isinstance(payload.get("priority"), str) else None,
            today,
        )
    if name == "add_subtask":
        scheduled = payload.get("scheduled_on")
        effort = payload.get("effort")
        return await forecast_add(
            store,
            str(payload["plan_id"]),
            str(payload["title"]),
            scheduled if isinstance(scheduled, str) else None,
            effort if isinstance(effort, str) else None,
            today,
        )
    changes = payload.get("changes")
    if not isinstance(changes, list):
        return ()
    return await forecast_reschedule(store, str(payload["plan_id"]), changes, today)
