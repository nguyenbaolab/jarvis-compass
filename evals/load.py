"""Đọc JSON bộ câu và bộ dữ liệu. Sai định dạng thì từ chối cả bộ."""

import json
import unicodedata
from datetime import date, datetime
from pathlib import Path

from core.plans import normalize_subtask_note

from evals.model import Case, Dataset, Expectation, Group, PlanSeed, SubtaskSeed, Suite

_KIND = {
    Group.CHI_KE_VIEC: "no_tool",
    Group.CHAO_HOI: "no_tool",
    Group.CAU_MO_HO: "no_tool",
    Group.CAU_NGOAI: "no_tool",
    Group.LAP_KE_HOACH: "one_create_plan",
    Group.HOI_DANH_SACH: "read_plans",
    Group.XEM_CHI_TIET: "read_detail",
    Group.CAP_NHAT: "update_status",
    Group.THEM_VIEC: "add_subtask",
    Group.GHI_CHU: "set_note",
    Group.HAN_LUU_NGAY: "create_with_deadline",
    Group.HAN_HOI_LAI: "ask_back_no_write",
    Group.NHOM_MO_HO: "ask_back_no_write",
    Group.HAN_CA_KE_HOACH: "set_deadline_existing",
    Group.DOI_HAN_TRUNG: "clash_two_turn",
    Group.DOI_NGAY: "reschedule_no_confirm",
    Group.TIN_DAI: "long_message_goal",
    Group.LIET_KE: "verbatim_titles",
    Group.GHI_NHAN: "observe",
    Group.UU_TIEN_NGUOI_DUNG: "create_with_priority",
    Group.DAT_UU_TIEN: "set_priority_existing",
    Group.DAT_SUC: "set_effort_existing",
    Group.QUA_TRONG_QUY: "load_within_budget",
    Group.QUA_VUOT: "load_over_budget",
    Group.QUA_XONG: "load_done_skipped",
    Group.QUA_SUC: "load_effort_hours",
    Group.QUA_CAU: "load_warning_sentence",
    Group.QUA_THU_TU: "load_move_order",
    Group.QUA_XAC_NHAN: "load_confirm_write",
    Group.QUA_TU_CHOI: "load_refusal",
}
_V3_GOAL = frozenset({
    "load_within_budget",
    "load_over_budget",
    "load_done_skipped",
    "load_confirm_write",
})
_V3_TITLE = frozenset({"load_within_budget", "load_done_skipped", "load_confirm_write"})
_V3_DATES = frozenset({
    "load_within_budget",
    "load_done_skipped",
    "load_move_order",
    "load_confirm_write",
})
_V3_NOTE = frozenset({
    "load_over_budget",
    "load_effort_hours",
    "load_warning_sentence",
    "load_move_order",
    "load_refusal",
})
_EXTRA = {
    "update_status": ("goal", "title", "status"),
    "add_subtask": ("goal", "title"),
    "set_note": ("goal", "title", "note"),
}
_EFFORTS = frozenset({"S", "M", "L"})
_PRIORITIES = frozenset({"high", "medium", "low"})
_STATUSES = frozenset({"pending", "done", "skipped"})


class LoadError(Exception):
    """Bộ câu hoặc bộ dữ liệu không đúng định dạng."""


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _optional_choice(raw: object, key: str, allowed: frozenset[str]) -> str | None:
    if not isinstance(raw, dict) or key not in raw or raw[key] is None:
        return None
    if not isinstance(raw[key], str) or raw[key] not in allowed:
        raise LoadError(f"{key} không hợp lệ.")
    return raw[key]


def _optional_date(raw: object, key: str) -> str | None:
    if not isinstance(raw, dict) or key not in raw or raw[key] is None:
        return None
    if not isinstance(raw[key], str):
        raise LoadError(f"{key} không phải ngày.")
    try:
        date.fromisoformat(raw[key])
    except ValueError as error:
        raise LoadError(f"{key} không phải ngày.") from error
    return raw[key]


def _aware_instant(raw: object) -> datetime | None:
    if not isinstance(raw, dict) or "instant" not in raw or raw["instant"] is None:
        return None
    if not isinstance(raw["instant"], str):
        raise LoadError("instant không phải chuỗi.")
    try:
        instant = datetime.fromisoformat(raw["instant"])
    except ValueError as error:
        raise LoadError("instant không phải mốc.") from error
    if instant.tzinfo is None:
        raise LoadError("instant không có múi giờ.")
    return instant


def _follow_up(raw: object) -> str | None:
    if not isinstance(raw, dict) or "follow_up" not in raw or raw["follow_up"] is None:
        return None
    if not isinstance(raw["follow_up"], str):
        raise LoadError("follow_up không phải chuỗi.")
    return _nfc(raw["follow_up"])


def _need_str(item: object, key: str) -> str:
    if not isinstance(item, dict) or key not in item or not isinstance(item[key], str):
        raise LoadError(f"Thiếu chuỗi {key}.")
    return _nfc(item[key])


def _load_dataset(path: Path, name: str) -> Dataset:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LoadError("Không đọc được bộ dữ liệu.") from error
    if not isinstance(payload, dict) or payload.get("name") != name:
        raise LoadError("Tên bộ dữ liệu không khớp file.")
    raw_plans = payload.get("plans")
    if not isinstance(raw_plans, list):
        raise LoadError("Bộ dữ liệu thiếu plans.")
    plans: list[PlanSeed] = []
    goals: set[str] = set()
    for raw_plan in raw_plans:
        if not isinstance(raw_plan, dict):
            raise LoadError("Kế hoạch không phải object.")
        goal = _need_str(raw_plan, "goal")
        if goal == "":
            raise LoadError("Mục tiêu rỗng.")
        if goal in goals:
            raise LoadError("Mục tiêu trùng.")
        goals.add(goal)
        raw_items = raw_plan.get("subtasks")
        if not isinstance(raw_items, list):
            raise LoadError("Thiếu việc con.")
        items: list[SubtaskSeed] = []
        titles: set[str] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                raise LoadError("Việc con không phải object.")
            title = _need_str(raw_item, "title")
            if title == "":
                raise LoadError("Tiêu đề rỗng.")
            status = _need_str(raw_item, "status")
            if status not in _STATUSES:
                raise LoadError("Trạng thái không hợp lệ.")
            if title in titles:
                raise LoadError("Tiêu đề trùng.")
            titles.add(title)
            note_raw = raw_item.get("note")
            if note_raw is not None and not isinstance(note_raw, str):
                raise LoadError("Ghi chú không phải chuỗi.")
            scheduled = _optional_date(raw_item, "scheduled_on")
            effort = _optional_choice(raw_item, "effort", _EFFORTS)
            items.append(
                SubtaskSeed(
                    title=title,
                    status=status,
                    note=normalize_subtask_note(note_raw),
                    scheduled_on=scheduled,
                    effort=effort,
                )
            )
        priority = _optional_choice(raw_plan, "priority", _PRIORITIES)
        plans.append(PlanSeed(goal=goal, subtasks=tuple(items), priority=priority))
    return Dataset(name=name, plans=tuple(plans))


def _expectation(group: Group, raw: object) -> Expectation:
    if not isinstance(raw, dict) or not isinstance(raw.get("kind"), str):
        raise LoadError("Kỳ vọng thiếu kind.")
    kind = _nfc(str(raw["kind"]))
    if kind != _KIND[group]:
        raise LoadError("kind không khớp nhóm.")
    extra = _EXTRA.get(kind, ())
    values: dict[str, str | None] = {}
    for key in extra:
        if key not in raw:
            raise LoadError(f"Kỳ vọng thiếu {key}.")
        if key == "note":
            note = raw[key]
            if not isinstance(note, str):
                raise LoadError("Ghi chú kỳ vọng không phải chuỗi.")
            values[key] = _nfc(note)
            continue
        if not isinstance(raw[key], str):
            raise LoadError(f"Kỳ vọng {key} không phải chuỗi.")
        values[key] = _nfc(str(raw[key]))
        if key in {"goal", "title"} and values[key] == "":
            raise LoadError(f"Kỳ vọng {key} rỗng.")
    if "status" in values and values["status"] not in _STATUSES:
        raise LoadError("Trạng thái kỳ vọng không hợp lệ.")
    deadline = _required_date(raw, "deadline") if kind in {"create_with_deadline", "set_deadline_existing"} else None
    goal = values.get("goal")
    other_goal = None
    dates = None
    history_moves = None
    titles = None
    priority = None
    effort = None
    title = values.get("title")
    if kind == "set_deadline_existing" and "goal" not in raw:
        raise LoadError("Kỳ vọng thiếu goal.")
    if kind == "set_deadline_existing":
        goal = _need_str(raw, "goal")
        if goal == "":
            raise LoadError("Kỳ vọng goal rỗng.")
    if kind == "verbatim_titles":
        titles = _title_list(raw)
    if kind in {"clash_two_turn", "reschedule_no_confirm"}:
        goal = _need_str(raw, "goal")
        dates = _date_pairs(raw)
        history_moves = _history_moves(raw)
        if goal == "":
            raise LoadError("Kỳ vọng goal rỗng.")
    if kind == "clash_two_turn":
        other_goal = _need_str(raw, "other_goal")
        if other_goal == "":
            raise LoadError("Kỳ vọng other_goal rỗng.")
    if kind == "create_with_priority":
        priority = _optional_choice(raw, "priority", _PRIORITIES)
        if priority is None:
            raise LoadError("Kỳ vọng thiếu priority.")
    if kind == "set_priority_existing":
        goal = _need_str(raw, "goal")
        if goal == "":
            raise LoadError("Kỳ vọng goal rỗng.")
        priority = _optional_choice(raw, "priority", _PRIORITIES)
        if priority is None:
            raise LoadError("Kỳ vọng thiếu priority.")
    if kind == "set_effort_existing":
        goal = _need_str(raw, "goal")
        title = _need_str(raw, "title")
        if goal == "" or title == "":
            raise LoadError("Kỳ vọng goal rỗng.")
        effort = _optional_choice(raw, "effort", _EFFORTS)
        if effort is None:
            raise LoadError("Kỳ vọng thiếu effort.")
    note = values.get("note")
    if kind in _V3_GOAL:
        goal = _need_str(raw, "goal")
        if goal == "":
            raise LoadError("Kỳ vọng goal rỗng.")
    if kind in _V3_TITLE:
        title = _need_str(raw, "title")
        if title == "":
            raise LoadError("Kỳ vọng title rỗng.")
    if kind == "load_confirm_write":
        other_goal = _need_str(raw, "other_goal")
        if other_goal == "":
            raise LoadError("Kỳ vọng other_goal rỗng.")
        history_moves = _history_moves(raw)
    if kind in _V3_DATES:
        dates = _date_pairs(raw)
    if kind in _V3_NOTE:
        note = _need_str(raw, "note")
        if note == "":
            raise LoadError("Kỳ vọng note rỗng.")
    return Expectation(
        kind=kind,
        goal=goal,
        title=title,
        status=values.get("status"),
        note=note,
        deadline=deadline,
        titles=titles,
        other_goal=other_goal,
        dates=dates,
        history_moves=history_moves,
        priority=priority,
        effort=effort,
    )


def _required_date(raw: dict[str, object], key: str) -> str:
    if key not in raw or not isinstance(raw[key], str):
        raise LoadError(f"Kỳ vọng thiếu {key}.")
    try:
        date.fromisoformat(raw[key])
    except ValueError as error:
        raise LoadError(f"Kỳ vọng {key} không phải ngày.") from error
    return raw[key]


def _title_list(raw: dict[str, object]) -> tuple[str, ...]:
    titles = raw.get("titles")
    if not isinstance(titles, list) or not titles:
        raise LoadError("Kỳ vọng thiếu titles.")
    found: list[str] = []
    for item in titles:
        if not isinstance(item, str) or _nfc(item) == "":
            raise LoadError("Kỳ vọng titles không phải chuỗi.")
        found.append(_nfc(item))
    return tuple(found)


def _date_pairs(raw: dict[str, object]) -> tuple[tuple[str, str], ...]:
    dates = raw.get("dates")
    if not isinstance(dates, list) or not dates:
        raise LoadError("Kỳ vọng thiếu dates.")
    pairs: list[tuple[str, str]] = []
    for item in dates:
        if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str) or not isinstance(item[1], str):
            raise LoadError("Kỳ vọng dates không hợp lệ.")
        title = _nfc(item[0])
        if title == "":
            raise LoadError("Kỳ vọng dates không hợp lệ.")
        try:
            date.fromisoformat(item[1])
        except ValueError as error:
            raise LoadError("Kỳ vọng dates không hợp lệ.") from error
        pairs.append((title, item[1]))
    return tuple(pairs)


def _history_moves(raw: dict[str, object]) -> int:
    value = raw.get("history_moves")
    if type(value) is not int:
        raise LoadError("Kỳ vọng thiếu history_moves.")
    return value


def _expectation_refers(dataset: Dataset, expectation: Expectation) -> None:
    goals = {item.goal: item for item in dataset.plans}
    if expectation.goal is not None and expectation.goal not in goals:
        raise LoadError("Kỳ vọng trỏ mục tiêu không có.")
    if expectation.other_goal is not None and expectation.other_goal not in goals:
        raise LoadError("Kỳ vọng trỏ mục tiêu không có.")
    plan = goals.get(expectation.goal or "")
    if expectation.kind == "load_move_order" and expectation.dates is not None:
        known = {item.title for seeded in dataset.plans for item in seeded.subtasks}
        if any(title not in known for title, _day in expectation.dates):
            raise LoadError("Kỳ vọng trỏ tiêu đề không có.")
    elif expectation.dates is not None and plan is not None:
        known = {item.title for item in plan.subtasks}
        added = {expectation.title} if expectation.title else set()
        if expectation.kind not in {"load_within_budget", "load_done_skipped", "load_confirm_write"}:
            added = set()
        if any(title not in known and title not in added for title, _day in expectation.dates):
            raise LoadError("Kỳ vọng trỏ tiêu đề không có.")
    if expectation.goal is None or plan is None:
        return
    if expectation.kind in {"update_status", "set_note", "set_effort_existing"}:
        if expectation.title is None or all(item.title != expectation.title for item in plan.subtasks):
            raise LoadError("Kỳ vọng trỏ tiêu đề không có.")


def _already_true(dataset: Dataset, expectation: Expectation) -> bool:
    if expectation.goal is None or expectation.title is None:
        return False
    for plan in dataset.plans:
        if plan.goal != expectation.goal:
            continue
        titles = [item.title for item in plan.subtasks]
        if expectation.kind == "add_subtask":
            return expectation.title in titles
        for item in plan.subtasks:
            if item.title != expectation.title:
                continue
            if expectation.kind == "update_status":
                return item.status == expectation.status
            if expectation.kind == "set_note":
                return item.note == normalize_subtask_note(expectation.note)
    return False


def load_suite(cases_path: Path, datasets_dir: Path) -> Suite:
    """Đọc một file câu và các file dữ liệu nó trỏ tới."""

    try:
        payload = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LoadError("Không đọc được bộ câu.") from error
    if not isinstance(payload, dict):
        raise LoadError("Bộ câu không phải object.")
    version = payload.get("cases_version")
    if type(version) is not int:
        raise LoadError("cases_version không phải số nguyên.")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise LoadError("Thiếu mảng cases.")
    cases: list[Case] = []
    seen: set[str] = set()
    datasets: dict[str, Dataset] = {}
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise LoadError("Câu không phải object.")
        case_id = _need_str(raw, "id")
        if case_id == "" or case_id in seen:
            raise LoadError("Id câu không hợp lệ.")
        seen.add(case_id)
        group_text = _need_str(raw, "group")
        try:
            group = Group(group_text)
        except ValueError as error:
            raise LoadError("Nhóm không hợp lệ.") from error
        message = _need_str(raw, "user_message")
        dataset_name = _need_str(raw, "dataset")
        instant = _aware_instant(raw)
        follow_up = _follow_up(raw)
        if version >= 2 and instant is None:
            raise LoadError("Ca v2 thiếu instant.")
        if "/" in dataset_name or "\\" in dataset_name:
            raise LoadError("Tên bộ dữ liệu có đường dẫn.")
        expectation = _expectation(group, raw.get("expectation"))
        dataset: Dataset | None = None
        if dataset_name != "":
            if dataset_name not in datasets:
                path = datasets_dir / f"{dataset_name}.json"
                if not path.is_file():
                    raise LoadError("Thiếu file bộ dữ liệu.")
                datasets[dataset_name] = _load_dataset(path, dataset_name)
            dataset = datasets[dataset_name]
            _expectation_refers(dataset, expectation)
            if _already_true(dataset, expectation):
                raise LoadError("Kỳ vọng đã đúng từ bộ dữ liệu.")
        elif expectation.goal is not None or expectation.other_goal is not None or expectation.dates:
            raise LoadError("Kỳ vọng trỏ mục tiêu không có.")
        if expectation.kind == "clash_two_turn" and (follow_up is None or dataset is None):
            raise LoadError("Ca trùng thiếu follow_up hoặc bộ dữ liệu.")
        if expectation.kind in {"load_confirm_write", "load_refusal"} and (
            follow_up is None or dataset is None
        ):
            raise LoadError("Ca hai lượt thiếu follow_up hoặc bộ dữ liệu.")
        cases.append(
            Case(
                id=case_id,
                group=group,
                user_message=message,
                dataset=dataset_name,
                expectation=expectation,
                instant=instant,
                follow_up=follow_up,
            )
        )
    return Suite(cases_version=version, cases=tuple(cases), datasets=datasets)
