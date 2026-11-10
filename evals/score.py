"""Bảy luật chấm một lần. Không đọc câu trả lời để nhận lỗi chạy."""

import re
import unicodedata
from dataclasses import dataclass

from core.plans import Plan, PlanStore, SubtaskStatus, normalize_subtask_note
from tools.tool_definitions import TOOL_DEFINITIONS

from evals.log_lines import parse_log_rows
from evals.model import Expectation

# Tăng khi đổi luật chấm trong file này hoặc cách phân loại lần trong evals/turn.py.
SCORER_VERSION = 3

_NO_TOOL = frozenset({"chỉ kể việc", "chào hỏi", "câu mơ hồ", "câu ngoài phạm vi"})
_WRITE_TOOL = {
    "cập nhật trạng thái việc con": "update_subtask",
    "thêm việc con": "add_subtask",
    "ghi chú": "set_subtask_note",
}
_READ_OK = frozenset({"get_plans", "get_plan_detail"})
_PREFIX = re.compile(r"^(?:ngày|tuần|bước|giai đoạn)\s*[0-9]+|^[0-9]+\.")
_SELF_NAME = "trợ lý lập kế hoạch"


@dataclass(frozen=True)
class StoreExpectation:
    """Kỳ vọng kho của một ca ghi."""

    kind: str
    goal: str
    title: str
    status: str | None = None
    note: str | None = None


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _tool_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if "tool" in row]


def _names(rows: list[dict[str, object]]) -> list[str]:
    return [str(row["tool"]) for row in _tool_rows(rows)]


def _tool_law(group: str, names: list[str]) -> str:
    if group in _NO_TOOL:
        return "pass" if not names else "fail"
    if group == "nhờ lập kế hoạch":
        return "pass" if names == ["create_plan"] else "fail"
    if group == "hỏi danh sách":
        return "pass" if names and all(name == "get_plans" for name in names) else "fail"
    if group == "xem chi tiết":
        others = [name for name in names if name != "get_plan_detail"]
        has_detail = "get_plan_detail" in names
        only_list = all(name == "get_plans" for name in others)
        return "pass" if has_detail and only_list else "fail"
    write_tool = _WRITE_TOOL.get(group)
    if write_tool is None:
        return "fail"
    allowed = _READ_OK | {write_tool}
    return "pass" if all(name in allowed for name in names) else "fail"


def _count_law(group: str, names: list[str]) -> str:
    count = sum(1 for name in names if name == "create_plan")
    expected = 1 if group == "nhờ lập kế hoạch" else 0
    return "pass" if count == expected else "fail"


def _required_law(rows: list[dict[str, object]]) -> str:
    for row in _tool_rows(rows):
        name = str(row["tool"])
        spec = TOOL_DEFINITIONS.get(name)
        if spec is None:
            return "fail"
        tool_input = row["input"]
        if not isinstance(tool_input, dict):
            return "fail"
        schema = spec["input_schema"]
        required = schema["required"] if isinstance(schema, dict) else []
        if isinstance(required, list) and any(key not in tool_input for key in required):
            return "fail"
    return "pass"


def _new_titles(rows: list[dict[str, object]], dataset_titles: frozenset[str]) -> list[str]:
    found: list[str] = []
    seeded = {_nfc(title) for title in dataset_titles}
    for row in _tool_rows(rows):
        tool_input = row["input"]
        if not isinstance(tool_input, dict):
            continue
        if row["tool"] == "create_plan":
            subtasks = tool_input.get("subtasks")
            if isinstance(subtasks, list):
                found.extend(_item_title(item) for item in subtasks)
        elif row["tool"] == "add_subtask" and "title" in tool_input:
            found.append(str(tool_input["title"]))
    return [title for title in found if _nfc(title) not in seeded]


def _item_title(item: object) -> str:
    if isinstance(item, dict) and "title" in item:
        return str(item["title"])
    return str(item)


def _prefix_law(titles: list[str]) -> str:
    for title in titles:
        folded = _nfc(title).casefold().lstrip()
        if _PREFIX.search(folded):
            return "fail"
    return "pass"


def _markdown_law(reply: str) -> str:
    text = _nfc(reply)
    if "```" in text or "`" in text or "**" in text or "__" in text or "](" in text:
        return "fail"
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            return "fail"
        if stripped.startswith("* "):
            return "fail"
    return "pass"


def _self_name_law(reply: str) -> str:
    return "fail" if _SELF_NAME in _nfc(reply) else "pass"


def _same(left: str, right: str) -> bool:
    return _nfc(left).strip() == _nfc(right).strip()


def _plan_for(plans: tuple[Plan, ...], goal: str) -> Plan | None:
    for plan in plans:
        if _same(plan.goal, goal):
            return plan
    return None


def _store_matches(plans: tuple[Plan, ...], expectation: StoreExpectation) -> bool:
    plan = _plan_for(plans, expectation.goal)
    if plan is None:
        return False
    if expectation.kind == "add_subtask":
        return any(_same(item.title, expectation.title) for item in plan.subtasks)
    for item in plan.subtasks:
        if not _same(item.title, expectation.title):
            continue
        if expectation.kind == "update_status":
            return item.status == SubtaskStatus(expectation.status or "")
        if expectation.kind == "set_note":
            return item.note == normalize_subtask_note(expectation.note)
    return False


async def _store_law(
    group: str,
    store: PlanStore | None,
    expectation: StoreExpectation | None,
) -> str:
    if group not in _WRITE_TOOL:
        return "not_applicable"
    if store is None or expectation is None:
        return "fail"
    plans = await store.list_newest_first()
    return "pass" if _store_matches(plans, expectation) else "fail"


async def law_results(
    group: str,
    reply: str,
    lines: list[str],
    *,
    store: PlanStore | None = None,
    expectation: StoreExpectation | None = None,
    dataset_titles: frozenset[str] = frozenset(),
    cases_version: int = 1,
    detail: Expectation | None = None,
    opening: tuple[object, ...] | None = None,
    after_first: tuple[object, ...] | None = None,
    closing: tuple[object, ...] | None = None,
    earlier_lines: list[str] | None = None,
    earlier_reply: str | None = None,
    history_count: int = 0,
) -> dict[str, str]:
    """Bảy luật. Ca v1 không đọc ngày, sức, ưu tiên hay lịch sử."""

    if cases_version == 2:
        return _v2_laws(
            reply,
            lines,
            detail=detail,
            opening=opening,
            after_first=after_first,
            closing=closing,
            earlier_lines=earlier_lines,
            earlier_reply=earlier_reply,
            history_count=history_count,
            dataset_titles=dataset_titles,
        )
    if cases_version == 3:
        return _v3_laws(
            reply,
            lines,
            detail=detail,
            opening=opening,
            after_first=after_first,
            closing=closing,
            earlier_lines=earlier_lines,
            earlier_reply=earlier_reply,
            history_count=history_count,
            dataset_titles=dataset_titles,
        )
    rows = parse_log_rows(lines)
    names = _names(rows)
    return {
        "tool": _tool_law(group, names),
        "create_plan_count": _count_law(group, names),
        "required": _required_law(rows),
        "prefix": _prefix_law(_new_titles(rows, dataset_titles)),
        "markdown": _markdown_law(reply),
        "self_name": _self_name_law(reply),
        "store": await _store_law(group, store, expectation),
    }


_CREATE_KINDS = frozenset(
    {"create_with_deadline", "long_message_goal", "verbatim_titles", "create_with_priority"}
)
_MOVE_OK = _READ_OK | {"reschedule_subtasks"}
_PRIORITY_OK = _READ_OK | {"set_plan_priority"}
_EFFORT_OK = _READ_OK | {"set_subtask_effort"}
_DATE_MARK = re.compile(
    r"\d{1,2}/\d{1,2}(?:/\d{4})?|\d{4}-\d{2}-\d{2}|(?i:(?:vào|trước|đến|hết|hạn|sau)\s+thứ\s+(?:hai|ba|tư|năm|sáu|bảy))|thứ (?:Hai|Ba|Tư|Năm|Sáu|Bảy)|(?i:chủ nhật|hôm nay|ngày mai|tuần này|tuần sau|cuối tuần)"
)
_TIME_MARK = re.compile(r"\d+\s*(?:giờ|tiếng)|\b\d+\s*h\b", re.IGNORECASE)


def store_image(plans: tuple[Plan, ...]) -> tuple[object, ...]:
    """Ảnh kho để so bằng ==. Thứ tự là thứ tự plans được truyền."""

    def priority(plan: Plan) -> str | None:
        return None if plan.priority is None else plan.priority.value

    def effort(item: object) -> str | None:
        value = getattr(item, "effort", None)
        return None if value is None else str(value.value)

    def day(item: object) -> str | None:
        value = getattr(item, "scheduled_on", None)
        return None if value is None else value.isoformat()

    return tuple(
        (
            plan.goal,
            priority(plan),
            tuple(
                (item.title, item.status.value, item.note, day(item), effort(item))
                for item in plan.subtasks
            ),
        )
        for plan in plans
    )


def _mark(flag: bool) -> str:
    return "pass" if flag else "fail"


def _confirm_true(row: dict[str, object]) -> bool:
    tool_input = row.get("input")
    return isinstance(tool_input, dict) and tool_input.get("confirm") is True


def _move_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if row.get("tool") == "reschedule_subtasks"]


def _subset(names: list[str], rows: list[dict[str, object]], *, need_move: bool, confirm: str) -> bool:
    if any(name not in _MOVE_OK for name in names):
        return False
    moves = _move_rows(rows)
    if need_move and not moves:
        return False
    if confirm == "none" and any(_confirm_true(row) for row in moves):
        return False
    if confirm == "some_true" and not any(_confirm_true(row) for row in moves):
        return False
    return True


def _v2_tool(kind: str, lines: list[str], earlier_lines: list[str] | None) -> str:
    rows = _tool_rows(parse_log_rows(lines))
    names = _names(parse_log_rows(lines))
    if kind in _CREATE_KINDS:
        return _mark(names == ["create_plan"])
    if kind == "ask_back_no_write":
        return _mark(all(name in _READ_OK for name in names))
    if kind == "set_deadline_existing":
        return _mark(_subset(names, rows, need_move=True, confirm="any"))
    if kind == "reschedule_no_confirm":
        return _mark(_subset(names, rows, need_move=True, confirm="none"))
    if kind == "clash_two_turn":
        earlier = earlier_lines or []
        first_rows = _tool_rows(parse_log_rows(earlier))
        first_names = _names(parse_log_rows(earlier))
        first_ok = _subset(first_names, first_rows, need_move=True, confirm="none")
        second_ok = _subset(names, rows, need_move=True, confirm="some_true")
        return _mark(first_ok and second_ok)
    if kind == "observe":
        return "not_applicable"
    if kind == "set_priority_existing":
        return _mark(all(name in _PRIORITY_OK for name in names) and "set_plan_priority" in names)
    if kind == "set_effort_existing":
        return _mark(all(name in _EFFORT_OK for name in names) and "set_subtask_effort" in names)
    return "fail"


def _v2_count(kind: str, lines: list[str], earlier_lines: list[str] | None) -> str:
    names = _names(parse_log_rows(lines))
    if earlier_lines:
        names = _names(parse_log_rows(earlier_lines)) + names
    count = sum(1 for name in names if name == "create_plan")
    expected = 1 if kind in _CREATE_KINDS else 0
    return _mark(count == expected)


def _plan_named(image: tuple[object, ...] | None, goal: str) -> tuple[object, ...] | None:
    if image is None:
        return None
    for plan in image:
        if isinstance(plan, tuple) and plan and plan[0] == goal:
            return plan
    return None


def _subtasks(plan: tuple[object, ...]) -> tuple[tuple[object, ...], ...]:
    items = plan[2]
    if not isinstance(items, tuple):
        return ()
    return tuple(item for item in items if isinstance(item, tuple))


def _last_pending_date(plan: tuple[object, ...]) -> str | None:
    pending = [item for item in _subtasks(plan) if item[1] == "pending"]
    if not pending:
        return None
    day = pending[-1][3]
    return day if isinstance(day, str) else None


def _latest_pending(plan: tuple[object, ...]) -> str | None:
    dates = [item[3] for item in _subtasks(plan) if item[1] == "pending" and isinstance(item[3], str)]
    if not dates:
        return None
    return max(dates)


def _goals_and_titles(image: tuple[object, ...] | None) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
    if image is None:
        return None
    found: list[tuple[str, tuple[str, ...]]] = []
    for plan in image:
        if not isinstance(plan, tuple):
            return None
        found.append((str(plan[0]), tuple(str(item[0]) for item in _subtasks(plan))))
    return tuple(found)


def _dates_match(plan: tuple[object, ...], dates: tuple[tuple[str, str], ...] | None) -> bool:
    if dates is None:
        return False
    actual = {str(item[0]): item[3] for item in _subtasks(plan)}
    expected = {title: day for title, day in dates}
    return actual == expected


def _others_same(opening: tuple[object, ...] | None, closing: tuple[object, ...] | None, goal: str) -> bool:
    if opening is None or closing is None:
        return False

    def rest(image: tuple[object, ...]) -> dict[object, object]:
        return {plan[0]: plan for plan in image if isinstance(plan, tuple) and plan[0] != goal}

    return rest(opening) == rest(closing)


def _efforts_blank(plan: tuple[object, ...]) -> bool:
    return all(item[4] is None for item in _subtasks(plan))


def _unset_priority_and_effort(plan: tuple[object, ...]) -> bool:
    return plan[1] is None and _efforts_blank(plan)


def _has_date(text: str) -> bool:
    return _DATE_MARK.search(_nfc(text)) is not None


def _has_time(text: str) -> bool:
    return _TIME_MARK.search(_nfc(text)) is not None


def _long_ok(plan: tuple[object, ...]) -> bool:
    goal = str(plan[0])
    if "\n" in goal or len(goal) >= 80 or _has_date(goal) or _has_time(goal):
        return False
    return all(not _has_date(str(item[0])) for item in _subtasks(plan))


def _verbatim(plan: tuple[object, ...], titles: tuple[str, ...] | None) -> bool:
    if titles is None:
        return False
    found = {_nfc(str(item[0])).strip() for item in _subtasks(plan)}
    return all(_nfc(title).strip() in found for title in titles)


def _priority_only(
    opening: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    goal: str | None,
    priority: str | None,
) -> bool:
    if opening is None or closing is None or goal is None or priority is None or len(opening) != len(closing):
        return False
    seen = False
    for left, right in zip(opening, closing, strict=True):
        if not isinstance(left, tuple) or not isinstance(right, tuple) or len(left) < 3 or len(right) < 3:
            return False
        if left[0] != goal:
            if left != right:
                return False
            continue
        seen = True
        if right[0] != goal or right[1] != priority or right[2] != left[2]:
            return False
    return seen


def _effort_only(
    opening: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    goal: str | None,
    title: str | None,
    effort: str | None,
) -> bool:
    if opening is None or closing is None or goal is None or title is None or effort is None:
        return False
    if len(opening) != len(closing):
        return False
    seen = False
    for left, right in zip(opening, closing, strict=True):
        if not isinstance(left, tuple) or not isinstance(right, tuple):
            return False
        if left[0] != goal:
            if left != right:
                return False
            continue
        if right[0] != goal or right[1] != left[1]:
            return False
        before = _subtasks(left)
        after = _subtasks(right)
        if len(before) != len(after):
            return False
        for old, new in zip(before, after, strict=True):
            if old[0] != title:
                if old != new:
                    return False
                continue
            seen = True
            if new[0] != title or new[4] != effort or new[:4] != old[:4]:
                return False
    return seen


def _v2_store(
    detail: Expectation | None,
    opening: tuple[object, ...] | None,
    after_first: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    history_count: int,
) -> str:
    if detail is None or detail.kind == "observe":
        return "not_applicable"
    kind = detail.kind
    if kind == "ask_back_no_write":
        return _mark(closing == opening and history_count == 0)
    if kind == "create_with_deadline":
        if closing is None or len(closing) != 1 or not isinstance(closing[0], tuple):
            return "fail"
        plan = closing[0]
        return _mark(
            _latest_pending(plan) == detail.deadline
            and _last_pending_date(plan) == detail.deadline
            and _unset_priority_and_effort(plan)
        )
    if kind == "set_deadline_existing":
        if _goals_and_titles(opening) != _goals_and_titles(closing) or detail.goal is None:
            return "fail"
        plan = _plan_named(closing, detail.goal)
        before = _plan_named(opening, detail.goal)
        if plan is None or before is None or _last_pending_date(plan) != detail.deadline:
            return "fail"
        pending_indexes = [index for index, item in enumerate(_subtasks(plan)) if item[1] == "pending"]
        if not pending_indexes:
            return "fail"
        last = pending_indexes[-1]
        before_items = _subtasks(before)
        for index, item in enumerate(_subtasks(plan)):
            if index == last:
                continue
            if item[3] != before_items[index][3]:
                return "fail"
        for left, right in zip(opening or (), closing or (), strict=True):
            if not isinstance(left, tuple) or not isinstance(right, tuple) or left[0] == detail.goal:
                continue
            if tuple(item[3] for item in _subtasks(left)) != tuple(item[3] for item in _subtasks(right)):
                return "fail"
        return "pass"
    if kind in {"reschedule_no_confirm", "clash_two_turn"}:
        if detail.goal is None or closing is None or opening is None:
            return "fail"
        if kind == "clash_two_turn" and after_first != opening:
            return "fail"
        plan = _plan_named(closing, detail.goal)
        if plan is None or not _dates_match(plan, detail.dates):
            return "fail"
        if kind == "reschedule_no_confirm" and not _others_same(opening, closing, detail.goal):
            return "fail"
        if kind == "clash_two_turn":
            other = _plan_named(closing, detail.other_goal or "")
            was = _plan_named(opening, detail.other_goal or "")
            if other is None or other != was:
                return "fail"
        return _mark(history_count == detail.history_moves)
    if kind == "long_message_goal":
        if closing is None or len(closing) != 1 or not isinstance(closing[0], tuple):
            return "fail"
        return _mark(_long_ok(closing[0]) and _unset_priority_and_effort(closing[0]))
    if kind == "verbatim_titles":
        if closing is None or len(closing) != 1 or not isinstance(closing[0], tuple):
            return "fail"
        return _mark(_verbatim(closing[0], detail.titles) and _unset_priority_and_effort(closing[0]))
    if kind == "create_with_priority":
        if closing is None or len(closing) != 1 or not isinstance(closing[0], tuple):
            return "fail"
        plan = closing[0]
        return _mark(plan[1] == detail.priority and _efforts_blank(plan))
    if kind == "set_priority_existing":
        return _mark(_priority_only(opening, closing, detail.goal, detail.priority))
    if kind == "set_effort_existing":
        return _mark(_effort_only(opening, closing, detail.goal, detail.title, detail.effort))
    return "fail"


def _v2_laws(
    reply: str,
    lines: list[str],
    *,
    detail: Expectation | None,
    opening: tuple[object, ...] | None,
    after_first: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    earlier_lines: list[str] | None,
    earlier_reply: str | None,
    history_count: int,
    dataset_titles: frozenset[str],
) -> dict[str, str]:
    kind = "" if detail is None else detail.kind
    rows = parse_log_rows(earlier_lines or []) + parse_log_rows(lines)
    replies = (reply,) if earlier_reply is None else (earlier_reply, reply)
    return {
        "tool": _v2_tool(kind, lines, earlier_lines),
        "create_plan_count": _v2_count(kind, lines, earlier_lines),
        "required": _required_law(rows),
        "prefix": _prefix_law(_new_titles(rows, dataset_titles)),
        "markdown": _mark(all(_markdown_law(item) == "pass" for item in replies)),
        "self_name": _mark(all(_self_name_law(item) == "pass" for item in replies)),
        "store": _v2_store(detail, opening, after_first, closing, history_count),
    }


_V3_TOOLS = _READ_OK | {"add_subtask", "create_plan", "reschedule_subtasks"}
_V3_CREATE = frozenset({"load_effort_hours", "load_warning_sentence"})
_HOUR_NUMBER = re.compile(r"(\d+)\s*giờ")
_CLAIMED_DONE = re.compile(r"\bĐã (thêm|ghi|tạo|lưu)\b")
_INVENTED_DESTINATION = re.compile(r"sang\s+\d{1,2}/\d{1,2}")
_PROVISIONAL_MARKERS = ("tính tạm", "ước tính", "tạm tính", "ước lượng", "chưa có sức")


def _day_mark(iso: str) -> str:
    _year, month, day = iso.split("-")
    return f"{int(day):02d}/{int(month):02d}"


def _reply_moves(reply: str, dates: tuple[tuple[str, str], ...] | None) -> bool:
    if not dates:
        return False
    cursor = 0
    for title, iso in dates:
        title_at = reply.find(title, cursor)
        if title_at < 0:
            return False
        day_at = reply.find(_day_mark(iso), title_at)
        if day_at < 0:
            return False
        cursor = day_at
    return "3. " not in reply


def _hours_ok(reply: str, detail: Expectation) -> bool:
    if detail.note is None:
        return True
    head = detail.note.split("(", 1)[0]
    numbers = _HOUR_NUMBER.findall(head)
    return all(re.search(rf"(?<!\d){number}\s*giờ", reply) is not None for number in numbers)


def _provisional_ok(reply: str, detail: Expectation) -> bool:
    if detail.note is None or "(tính tạm" not in detail.note:
        return True
    return any(marker in reply for marker in _PROVISIONAL_MARKERS)


def _asks_owner(reply: str) -> bool:
    return "?" in reply and _CLAIMED_DONE.search(reply) is None


def _said(reply: str, detail: Expectation) -> bool:
    return _asks_owner(reply) and _hours_ok(reply, detail) and _provisional_ok(reply, detail)


def _confirmed_add_with_moves(row: dict[str, object]) -> bool:
    if str(row.get("tool")) != "add_subtask" or not _confirm_true(row):
        return False
    tool_input = row.get("input")
    if not isinstance(tool_input, dict):
        return False
    moves = tool_input.get("load_moves")
    return isinstance(moves, list) and len(moves) > 0


def _parsed_rows(lines: list[str] | None) -> list[dict[str, object]]:
    return parse_log_rows(lines or [])


def _v3_tool(
    kind: str,
    lines: list[str],
    earlier_lines: list[str] | None,
    reply: str,
    earlier_reply: str | None,
    detail: Expectation | None,
) -> str:
    if detail is None:
        return "fail"
    rows = _tool_rows(_parsed_rows(lines))
    names = _names(_parsed_rows(lines))
    if any(name not in _V3_TOOLS for name in names):
        return "fail"
    if kind in {"load_within_budget", "load_done_skipped"}:
        return _mark("add_subtask" in names and "Lần này chưa ghi" not in reply)
    if kind == "load_over_budget":
        called = "add_subtask" in names or "create_plan" in names
        return _mark(called and _said(reply, detail))
    if kind == "load_effort_hours":
        return _mark("create_plan" in names and _said(reply, detail))
    if kind == "load_warning_sentence":
        clean = _INVENTED_DESTINATION.search(reply) is None
        return _mark("create_plan" in names and _said(reply, detail) and clean)
    if kind == "load_move_order":
        return _mark("add_subtask" in names and _said(reply, detail) and _reply_moves(reply, detail.dates))
    if kind == "load_confirm_write":
        first_rows = _tool_rows(_parsed_rows(earlier_lines))
        wrote = any(_confirmed_add_with_moves(row) for row in rows)
        no_reschedule = "reschedule_subtasks" not in names
        first_clean = not any(_confirm_true(row) for row in first_rows)
        warned = earlier_reply is not None and _asks_owner(earlier_reply)
        return _mark(wrote and no_reschedule and first_clean and warned)
    if kind == "load_refusal":
        text = earlier_reply if earlier_reply is not None else reply
        first_names = names if earlier_lines is None else _names(_parsed_rows(earlier_lines))
        return _mark("add_subtask" in first_names and _said(text, detail))
    return "fail"


def _v3_count(kind: str, lines: list[str], earlier_lines: list[str] | None) -> str:
    names = _names(_parsed_rows(lines)) + _names(_parsed_rows(earlier_lines))
    count = sum(1 for name in names if name == "create_plan")
    return _mark(count == (1 if kind in _V3_CREATE else 0))


def _turn_confirmed(lines: list[str], earlier_lines: list[str] | None) -> bool:
    rows = _tool_rows(_parsed_rows(lines)) + _tool_rows(_parsed_rows(earlier_lines))
    return any(_confirm_true(row) for row in rows)


def _v3_store(
    kind: str,
    detail: Expectation | None,
    opening: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    after_first: tuple[object, ...] | None,
    history_count: int,
    confirmed: bool = False,
) -> str:
    if detail is None or opening is None or closing is None:
        return "fail"
    if kind == "load_refusal":
        return _mark(closing == opening)
    if kind in {"load_over_budget", "load_effort_hours", "load_warning_sentence", "load_move_order"}:
        return _mark(closing == opening and history_count == 0)
    if kind in {"load_within_budget", "load_done_skipped"}:
        if detail.goal is None:
            return "fail"
        plan = _plan_named(closing, detail.goal)
        return _mark(
            history_count == 0
            and plan is not None
            and _dates_match(plan, detail.dates)
            and _others_same(opening, closing, detail.goal)
        )
    if kind == "load_confirm_write":
        if after_first != opening or detail.goal is None or detail.history_moves is None:
            return "fail"
        plan = _plan_named(closing, detail.goal)
        other = _plan_named(closing, detail.other_goal or "")
        was = _plan_named(opening, detail.other_goal or "")
        return _mark(
            history_count == detail.history_moves
            and plan is not None
            and _dates_match(plan, detail.dates)
            and other is not None
            and other == was
        )
    return "fail"


def _v3_laws(
    reply: str,
    lines: list[str],
    *,
    detail: Expectation | None,
    opening: tuple[object, ...] | None,
    after_first: tuple[object, ...] | None,
    closing: tuple[object, ...] | None,
    earlier_lines: list[str] | None,
    earlier_reply: str | None,
    history_count: int,
    dataset_titles: frozenset[str],
) -> dict[str, str]:
    kind = "" if detail is None else detail.kind
    rows = parse_log_rows(earlier_lines or []) + parse_log_rows(lines)
    replies = (reply,) if earlier_reply is None else (earlier_reply, reply)
    return {
        "tool": _v3_tool(kind, lines, earlier_lines, reply, earlier_reply, detail),
        "create_plan_count": _v3_count(kind, lines, earlier_lines),
        "required": _required_law(rows),
        "prefix": _prefix_law(_new_titles(rows, dataset_titles)),
        "markdown": _mark(all(_markdown_law(item) == "pass" for item in replies)),
        "self_name": _mark(all(_self_name_law(item) == "pass" for item in replies)),
        "store": _v3_store(
            kind,
            detail,
            opening,
            closing,
            after_first,
            history_count,
            confirmed=_turn_confirmed(lines, earlier_lines),
        ),
    }
