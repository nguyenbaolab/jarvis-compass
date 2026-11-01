"""Bảy luật chấm một lần. Không đọc câu trả lời để nhận lỗi chạy."""

import re
import unicodedata
from dataclasses import dataclass

from core.plans import Plan, PlanStore, SubtaskStatus, normalize_subtask_note
from tools.tool_definitions import TOOL_DEFINITIONS

from evals.log_lines import parse_log_rows

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
                found.extend(str(item) for item in subtasks)
        elif row["tool"] == "add_subtask" and "title" in tool_input:
            found.append(str(tool_input["title"]))
    return [title for title in found if _nfc(title) not in seeded]


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
) -> dict[str, str]:
    """Bảy luật. Luật kho là not_applicable ngoài ba nhóm ghi."""

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
