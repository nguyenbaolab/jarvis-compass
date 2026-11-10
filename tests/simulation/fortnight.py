"""Kịch bản 14 ngày cố định, bắt đầu thứ Hai 2026-11-16."""

from datetime import date, timedelta

from core.plans import Effort, Priority, SubtaskStatus, day_budget, day_load

from tests.simulation.harness import (
    BotOwner,
    DayClock,
    MemoryPlanStore,
    World,
    describe_moves,
    fence,
    find_plan,
    find_task,
    fingerprint,
    forecast_add,
    forecast_reschedule,
    day_heading,
    move_fragment,
    moves_payload,
    sentence_move_count,
    show_output,
)

_START = date(2026, 11, 16)
_HEADER = """# Mô phỏng 14 ngày

Bắt đầu thứ Hai 2026-11-16. Mỗi sáng 08:00 giờ Helsinki, now cố định.
Bản ghi không in mã kế hoạch hay mã việc. Kết quả JSON của tool bỏ khóa id; mọi câu không phải JSON giữ nguyên chữ của tool.
Tải là day_load sau hành động trong ngày. Mốc hôm nay là ngày của tin sáng, nên ngày trước mốc đó có tải 0.
"""

_OBSERVATIONS = """## Quan sát

(a) Việc quá hạn không bị tự dời và vẫn đứng đầu tin sáng của kế hoạch với ngày đã qua, vì chủ bot không đánh dấu xong.
(b) Việc của ngày đã qua tính 0 giờ vào tải ngày đó và không dồn vào hôm nay.
(c) Lần gọi đầu bị cảnh báo thì không ghi gì, lần xác nhận ghi cả việc xin và các việc dời.
(d) Việc không có sức tính 3 giờ và câu cảnh báo ghi "tính tạm".
"""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class _Transcript:
    def __init__(self) -> None:
        self.days: list[str] = []

    def add_day(
        self,
        index: int,
        day: date,
        morning: str,
        actions: list[str],
        loads: list[str] | None,
    ) -> None:
        body = "Không có." if not actions else "\n\n".join(actions)
        parts = [
            day_heading(index, day),
            "",
            "### Tin 08:00",
            "",
            fence(morning),
            "",
            "### Hành động",
            "",
            body,
        ]
        if actions:
            parts.extend(["", "### Tải", "", "\n".join(loads or [])])
        self.days.append("\n".join(parts))

    def render(self) -> str:
        return (
            _HEADER.rstrip()
            + "\n\n"
            + _OBSERVATIONS.strip()
            + "\n\n"
            + "\n\n".join(self.days)
            + "\n"
        )


def _action(number: int, label: str, output: str) -> str:
    return f"{number}. {label}\n\nKết quả:\n\n{fence(show_output(output))}"


def _note(number: int, text: str) -> str:
    return f"{number}. {text}"


async def _loads(store: MemoryPlanStore, today: date) -> list[str]:
    plans = await store.list_newest_first()
    days = sorted(
        {
            item.scheduled_on
            for plan in plans
            for item in plan.subtasks
            if item.scheduled_on is not None
        }
    )
    if not days:
        return ["Không có ngày nào đang có việc."]
    ordered = sorted(plans, key=lambda plan: plan.created_order)
    lines: list[str] = []
    for day in days:
        load = day_load(tuple(ordered), day, today)
        names = []
        for plan in ordered:
            for item in plan.subtasks:
                if item.scheduled_on != day:
                    continue
                names.append(f"{item.title} ({plan.goal}, {item.status.value})")
        lines.append(
            f"- {day.isoformat()}: {load.total} giờ, tính tạm {load.provisional}, "
            f"quỹ {day_budget(day)}. {'; '.join(names)}"
        )
    return lines


async def _one(plans, goal: str, title: str):
    plan = next(item for item in plans if item.goal == goal)
    task = next(item for item in plan.subtasks if item.title == title)
    return plan, task


async def build_fortnight_markdown() -> str:
    """Dựng bản ghi 14 ngày. Ném RuntimeError nếu kịch bản không ra đúng cảnh báo."""

    store = MemoryPlanStore()
    world = World(store)
    owner = BotOwner(store)
    transcript = _Transcript()
    mornings: list[str] = []
    provisional = ""

    for offset in range(14):
        day = _START + timedelta(days=offset)
        index = offset + 1
        send = await world.morning(at_morning(day))
        mornings.append(send.text)
        actions: list[str] = []
        if index == 1:
            actions.extend(await _day_one(owner, store, day))
        elif index == 2:
            actions.extend(await _day_two(owner, store, day))
        elif index == 3:
            actions.extend(await _day_three(owner, store, day))
        elif index == 4:
            actions.extend(await _day_four(owner, store, day))
        elif index == 5:
            actions.extend(await _day_five(owner, store, day))
            provisional = "\n".join(actions)
        loads = None if not actions else await _loads(store, day)
        transcript.add_day(index, day, send.text, actions, loads)

    _need(mornings[0] == "Không còn việc chưa làm.", "Sáng ngày 1 không trống.")
    for morning in mornings[1:]:
        _need("Nghe hội thoại (thứ Hai 16/11)" in morning, "Tin sáng thiếu việc quá hạn.")
    _need("tính tạm: 3 việc chưa có sức" in provisional, "Chưa thấy tính tạm.")
    text = transcript.render()
    from tests.simulation.harness import assert_no_ids

    assert_no_ids(text)
    _need("cũng đến hạn" in text, "Thiếu cảnh báo trùng hạn.")
    _need(text.count("Lần này chưa ghi.") >= 4, "Thiếu cảnh báo chưa ghi.")
    return text


def at_morning(day: date):
    from tests.simulation.harness import at_helsinki

    return at_helsinki(day, 8, 0)


async def _day_one(owner: BotOwner, store: MemoryPlanStore, day: date) -> list[str]:
    clock = DayClock(day)
    actions: list[str] = []
    finnish = {
        "goal": "Học tiếng Phần Lan",
        "priority": "medium",
        "subtasks": [
            {"title": "Nghe hội thoại", "scheduled_on": "2026-11-16", "effort": "S"},
            {"title": "Luyện nói", "scheduled_on": "2026-11-18", "effort": "S"},
            {"title": "Ôn từ vựng", "scheduled_on": "2026-11-20", "effort": "S"},
        ],
    }
    azure = {
        "goal": "Azure",
        "priority": "low",
        "subtasks": [
            {"title": "Học module 3", "scheduled_on": "2026-11-17", "effort": "L"},
            {"title": "Làm lab", "scheduled_on": "2026-11-19", "effort": "S"},
            {"title": "Ôn chứng chỉ", "scheduled_on": "2026-11-22", "effort": "S"},
        ],
    }
    for number, payload, label in (
        (1, finnish, "create_plan «Học tiếng Phần Lan», ưu tiên vừa (medium)"),
        (2, azure, "create_plan «Azure», ưu tiên thấp (low)"),
    ):
        result = await owner.tool("create_plan", payload, clock.next())
        _need(result.success and "Lần này chưa ghi." not in result.output, label)
        actions.append(_action(number, _with_tasks(label, payload["subtasks"]), result.output))
    plans = await store.list_newest_first()
    finnish_plan, _heard = await _one(plans, "Học tiếng Phần Lan", "Nghe hội thoại")
    azure_plan, module = await _one(plans, "Azure", "Học module 3")
    _need(finnish_plan.priority is Priority.MEDIUM, "Ưu tiên Phần Lan.")
    _need(azure_plan.priority is Priority.LOW, "Ưu tiên Azure.")
    _need(module.effort is Effort.L, "Module 3 không phải 6 giờ.")
    return actions


def _with_tasks(label: str, subtasks: list[dict[str, str]]) -> str:
    lines = [label, ""]
    for item in subtasks:
        lines.append(
            f"- {item['title']}, ngày {item['scheduled_on']}, sức {item['effort']}"
        )
    return "\n".join(lines)


async def _day_two(owner: BotOwner, store: MemoryPlanStore, day: date) -> list[str]:
    clock = DayClock(day)
    instant = clock.next()
    catalog = await owner.catalog(instant)
    plan = find_plan(catalog, "Azure")
    payload: dict[str, object] = {
        "plan_id": plan["id"],
        "title": "Thi thử",
        "scheduled_on": "2026-11-17",
        "effort": "L",
    }
    warned = await owner.tool("add_subtask", payload, instant)
    _need(warned.success and "trên quỹ" in warned.output, "Ngày 2 không cảnh báo vượt quỹ.")
    before = await fingerprint(store)
    moves = await forecast_add(store, str(plan["id"]), "Thi thử", "2026-11-17", "L", day)
    _need(sentence_move_count(warned.output) == len(moves), "Danh sách dời ngày 2 lệch.")
    for move in moves:
        _need(move_fragment(move) in warned.output, "Câu tool không có việc propose_load_moves đề xuất.")
    _need(await fingerprint(store) == before, "Cảnh báo ngày 2 đã ghi.")
    confirm = dict(payload)
    confirm["confirm"] = True
    confirm["load_moves"] = moves_payload(moves)
    saved = await owner.tool("add_subtask", confirm, clock.next())
    _need(saved.success and "Lần này chưa ghi." not in saved.output, "Ngày 2 xác nhận không ghi.")
    plans = await store.list_newest_first()
    _azure, module = await _one(plans, "Azure", "Học module 3")
    _azure, trial = await _one(plans, "Azure", "Thi thử")
    _need(module.scheduled_on == date(2026, 11, 18), "Học module 3 chưa được dời.")
    _need(trial.scheduled_on == date(2026, 11, 17) and trial.effort is Effort.L, "Thi thử chưa vào ngày 17.")
    return [
        _action(
            1,
            "add_subtask «Thi thử» vào kế hoạch «Azure», ngày 2026-11-17, sức L (6 giờ)",
            warned.output,
        ),
        _action(
            2,
            "add_subtask xác nhận «Thi thử» vào kế hoạch «Azure», ngày 2026-11-17, "
            f"sức L (6 giờ). Dời: {describe_moves(moves)}",
            saved.output,
        ),
    ]


async def _day_three(owner: BotOwner, store: MemoryPlanStore, day: date) -> list[str]:
    clock = DayClock(day)
    instant = clock.next()
    catalog = await owner.catalog(instant)
    plan = find_plan(catalog, "Học tiếng Phần Lan")
    payload = {
        "plan_id": plan["id"],
        "title": "Đọc thêm",
        "scheduled_on": "2026-11-18",
        "effort": "L",
    }
    before = await fingerprint(store)
    warned = await owner.tool("add_subtask", payload, instant)
    after = await fingerprint(store)
    _need(warned.success and "trên quỹ" in warned.output, "Ngày 3 không có cảnh báo khác.")
    _need(before == after, "Ngày 3 từ chối nhưng kho đổi.")
    _need("Đọc thêm" not in warned.output or "chưa ghi" in warned.output, "Ngày 3 đã ghi việc.")
    plans = await store.list_newest_first()
    titles = [item.title for item in plans for item in item.subtasks]
    _need("Đọc thêm" not in titles, "Việc bị từ chối vẫn nằm trong kho.")
    return [
        _action(
            1,
            "add_subtask «Đọc thêm» vào kế hoạch «Học tiếng Phần Lan», ngày 2026-11-18, sức L (6 giờ)",
            warned.output,
        ),
        _note(2, "Chủ bot từ chối. Kho không đổi."),
    ]


async def _day_four(owner: BotOwner, store: MemoryPlanStore, day: date) -> list[str]:
    clock = DayClock(day)
    actions: list[str] = []
    actions.append(await _mark_done(owner, clock, 1, "Học tiếng Phần Lan", "Luyện nói"))
    actions.append(await _mark_done(owner, clock, 2, "Azure", "Làm lab"))
    instant = clock.next()
    catalog = await owner.catalog(instant)
    plan = find_plan(catalog, "Học tiếng Phần Lan")
    task = find_task(plan, "Ôn từ vựng")
    payload = {
        "plan_id": plan["id"],
        "changes": [{"subtask_id": task["id"], "scheduled_on": "2026-11-22"}],
    }
    before = await fingerprint(store)
    warned = await owner.tool("reschedule_subtasks", payload, instant)
    _need(warned.success and "cũng đến hạn" in warned.output, "Ngày 4 không báo trùng hạn.")
    _need("trên quỹ" not in warned.output, "Ngày 4 lẫn vượt quỹ.")
    _need(await fingerprint(store) == before, "Cảnh báo trùng hạn đã ghi.")
    moves = await forecast_reschedule(store, str(plan["id"]), payload["changes"], day)
    _need(moves == (), "Trùng hạn ngày 4 không được kèm danh sách dời.")
    confirm = dict(payload)
    confirm["confirm"] = True
    saved = await owner.tool("reschedule_subtasks", confirm, clock.next())
    _need(saved.success and "chưa ghi" not in saved.output, "Ngày 4 xác nhận không ghi.")
    plans = await store.list_newest_first()
    _finnish, vocab = await _one(plans, "Học tiếng Phần Lan", "Ôn từ vựng")
    _finnish, talk = await _one(plans, "Học tiếng Phần Lan", "Luyện nói")
    _azure, lab = await _one(plans, "Azure", "Làm lab")
    _need(vocab.scheduled_on == date(2026, 11, 22), "Ôn từ vựng chưa sang ngày trùng hạn.")
    _need(talk.status is SubtaskStatus.DONE and lab.status is SubtaskStatus.DONE, "Chưa xong hai việc.")
    actions.append(
        _action(
            3,
            "reschedule_subtasks «Ôn từ vựng» trong kế hoạch «Học tiếng Phần Lan» sang 2026-11-22",
            warned.output,
        )
    )
    actions.append(
        _action(
            4,
            "reschedule_subtasks xác nhận «Ôn từ vựng» trong kế hoạch «Học tiếng Phần Lan» "
            "sang 2026-11-22",
            saved.output,
        )
    )
    return actions


async def _mark_done(owner: BotOwner, clock: DayClock, number: int, goal: str, title: str) -> str:
    instant = clock.next()
    catalog = await owner.catalog(instant)
    plan = find_plan(catalog, goal)
    task = find_task(plan, title)
    result = await owner.tool(
        "update_subtask",
        {"plan_id": plan["id"], "subtask_id": task["id"], "status": "done"},
        instant,
    )
    _need(result.success and "chưa ghi" not in result.output, f"Không đánh dấu xong {title}.")
    return _action(number, f"update_subtask «{title}» trong kế hoạch «{goal}» thành done", result.output)


async def _day_five(owner: BotOwner, store: MemoryPlanStore, day: date) -> list[str]:
    clock = DayClock(day)
    titles = ("Nghe podcast", "Đọc tin", "Viết nhật ký")
    actions: list[str] = []
    outputs: list[str] = []
    for number, title in enumerate(titles, start=1):
        instant = clock.next()
        catalog = await owner.catalog(instant)
        plan = find_plan(catalog, "Học tiếng Phần Lan")
        payload = {
            "plan_id": plan["id"],
            "title": title,
            "scheduled_on": "2026-11-21",
        }
        result = await owner.tool("add_subtask", payload, instant)
        _need(result.success, f"Lần thêm {title} thất bại.")
        outputs.append(result.output)
        actions.append(
            _action(
                number,
                f"add_subtask «{title}» vào kế hoạch «Học tiếng Phần Lan», "
                "ngày 2026-11-21, không sức",
                result.output,
            )
        )
    _need("Lần này chưa ghi." not in outputs[0], "Lần thêm không sức thứ nhất đã chặn.")
    _need("Lần này chưa ghi." not in outputs[1], "Lần thêm không sức thứ hai đã chặn.")
    _need("tính tạm: 3 việc chưa có sức" in outputs[2], "Lần thứ ba không nêu tính tạm.")
    plans = await store.list_newest_first()
    finnish = next(item for item in plans if item.goal == "Học tiếng Phần Lan")
    stored = {item.title for item in finnish.subtasks}
    _need("Nghe podcast" in stored and "Đọc tin" in stored, "Hai việc không sức chưa vào kho.")
    _need("Viết nhật ký" not in stored, "Lần bị cảnh báo vẫn ghi việc không sức.")
    actions.append(_note(4, "Chủ bot từ chối lần thứ ba. Kho giữ hai việc không sức."))
    return actions
