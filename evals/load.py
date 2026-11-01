"""Đọc JSON bộ câu và bộ dữ liệu. Sai định dạng thì từ chối cả bộ."""

import json
import unicodedata
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
}
_EXTRA = {
    "update_status": ("goal", "title", "status"),
    "add_subtask": ("goal", "title"),
    "set_note": ("goal", "title", "note"),
}
_STATUSES = frozenset({"pending", "done", "skipped"})


class LoadError(Exception):
    """Bộ câu hoặc bộ dữ liệu không đúng định dạng."""


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


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
            items.append(SubtaskSeed(title=title, status=status, note=normalize_subtask_note(note_raw)))
        plans.append(PlanSeed(goal=goal, subtasks=tuple(items)))
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
    return Expectation(kind=kind, goal=values.get("goal"), title=values.get("title"), status=values.get("status"), note=values.get("note"))


def _expectation_refers(dataset: Dataset, expectation: Expectation) -> None:
    if expectation.goal is None:
        return
    plan = next((item for item in dataset.plans if item.goal == expectation.goal), None)
    if plan is None:
        raise LoadError("Kỳ vọng trỏ mục tiêu không có.")
    if expectation.kind in {"update_status", "set_note"}:
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
        cases.append(Case(id=case_id, group=group, user_message=message, dataset=dataset_name, expectation=expectation))
    return Suite(cases_version=version, cases=tuple(cases), datasets=datasets)
