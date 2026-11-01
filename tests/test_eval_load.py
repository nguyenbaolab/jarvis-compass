"""Đọc bộ câu và bộ dữ liệu từ JSON tạm. Không ghi evals/cases/."""

import json
import unicodedata
from pathlib import Path

import pytest

from evals.load import LoadError, load_suite

_GROUPS = {
    "no_tool": "chỉ kể việc",
    "one_create_plan": "nhờ lập kế hoạch",
    "read_plans": "hỏi danh sách",
    "read_detail": "xem chi tiết",
    "update_status": "cập nhật trạng thái việc con",
    "add_subtask": "thêm việc con",
    "set_note": "ghi chú",
}


def _case(group: str, kind: str, dataset: str = "", extra: dict[str, object] | None = None) -> dict[str, object]:
    expectation: dict[str, object] = {"kind": kind}
    if extra:
        expectation.update(extra)
    return {
        "id": kind,
        "group": group,
        "user_message": "một câu",
        "dataset": dataset,
        "expectation": expectation,
    }


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _suite(tmp_path: Path, cases: list[object], datasets: dict[str, object] | None = None) -> object:
    cases_path = tmp_path / "cases.json"
    data_dir = tmp_path / "datasets"
    data_dir.mkdir(exist_ok=True)
    _write(cases_path, {"cases_version": 1, "cases": cases})
    for name, payload in (datasets or {}).items():
        _write(data_dir / f"{name}.json", payload)
    return load_suite(cases_path, data_dir)


def test_reads_version_and_empty_dataset(tmp_path: Path) -> None:
    """Bộ đúng định dạng, dataset rỗng thì không mở file."""

    loaded = _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "")])
    assert loaded.cases_version == 1
    assert loaded.cases[0].dataset == ""
    assert loaded.datasets == {}


def test_reads_dataset_plans_in_order(tmp_path: Path) -> None:
    """Bộ dữ liệu giữ thứ tự kế hoạch và việc con."""

    dataset = {
        "name": "kho",
        "plans": [
            {
                "goal": "Đọc sách",
                "subtasks": [
                    {"title": "Chương 1", "status": "pending", "note": None},
                    {"title": "Chương 2", "status": "done", "note": "xong"},
                ],
            }
        ],
    }
    loaded = _suite(
        tmp_path,
        [_case("cập nhật trạng thái việc con", "update_status", "kho", {"goal": "Đọc sách", "title": "Chương 1", "status": "done"})],
        {"kho": dataset},
    )
    plan = loaded.datasets["kho"].plans[0]
    assert plan.goal == "Đọc sách"
    assert [item.title for item in plan.subtasks] == ["Chương 1", "Chương 2"]


def test_rejects_bad_shape(tmp_path: Path) -> None:
    """Id trùng, nhóm lạ, kind lệch, file dữ liệu thiếu, mục tiêu trùng, tiêu đề trùng."""

    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool"), _case("chỉ kể việc", "no_tool")])
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("không có nhóm", "no_tool")])
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "one_create_plan")])
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "thiếu")])
    duplicated = {
        "name": "trung",
        "plans": [
            {"goal": "Một", "subtasks": []},
            {"goal": "Một", "subtasks": []},
        ],
    }
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "trung")], {"trung": duplicated})
    titles = {
        "name": "tieu",
        "plans": [
            {
                "goal": "Một",
                "subtasks": [
                    {"title": "Việc", "status": "pending", "note": None},
                    {"title": "Việc", "status": "done", "note": None},
                ],
            }
        ],
    }
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "tieu")], {"tieu": titles})


def test_rejects_expectation_already_true(tmp_path: Path) -> None:
    """Kỳ vọng ghi đã đúng từ bộ dữ liệu là sai định dạng."""

    base = {
        "name": "kho",
        "plans": [
            {
                "goal": "Đọc sách",
                "subtasks": [{"title": "Chương 1", "status": "done", "note": "đã nộp"}],
            }
        ],
    }
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [_case("cập nhật trạng thái việc con", "update_status", "kho", {"goal": "Đọc sách", "title": "Chương 1", "status": "done"})],
            {"kho": base},
        )
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [_case("ghi chú", "set_note", "kho", {"goal": "Đọc sách", "title": "Chương 1", "note": "đã nộp"})],
            {"kho": base},
        )
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [_case("thêm việc con", "add_subtask", "kho", {"goal": "Đọc sách", "title": "Chương 1"})],
            {"kho": base},
        )


def test_nfc_on_read(tmp_path: Path) -> None:
    """Chuỗi tổ hợp được đọc thành NFC."""

    composed = "việc"
    combining = unicodedata.normalize("NFD", composed)
    assert combining != composed
    loaded = _suite(
        tmp_path,
        [
            {
                "id": "n",
                "group": "chỉ kể việc",
                "user_message": combining,
                "dataset": "",
                "expectation": {"kind": "no_tool"},
            }
        ],
    )
    assert loaded.cases[0].user_message == composed


def test_rejects_slash_in_dataset_name(tmp_path: Path) -> None:
    """Tên bộ dữ liệu không chứa dấu phân cách thư mục."""

    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "a/b")])


def test_rejects_empty_goal_or_title_in_dataset(tmp_path: Path) -> None:
    """Mục tiêu hoặc tiêu đề rỗng sau NFC và strip trong bộ dữ liệu bị từ chối."""

    empty_goal = {
        "name": "trong-goal",
        "plans": [{"goal": "   ", "subtasks": [{"title": "Việc", "status": "pending", "note": None}]}],
    }
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "trong-goal")], {"trong-goal": empty_goal})
    empty_title = {
        "name": "trong-title",
        "plans": [{"goal": "Đọc", "subtasks": [{"title": "  ", "status": "pending", "note": None}]}],
    }
    with pytest.raises(LoadError):
        _suite(tmp_path, [_case("chỉ kể việc", "no_tool", "trong-title")], {"trong-title": empty_title})


def test_rejects_expectation_missing_goal_or_title(tmp_path: Path) -> None:
    """Kỳ vọng nhóm ghi trỏ mục tiêu hoặc tiêu đề không có trong bộ dữ liệu bị từ chối."""

    base = {
        "name": "kho",
        "plans": [
            {
                "goal": "Đọc sách",
                "subtasks": [{"title": "Chương 1", "status": "pending", "note": None}],
            }
        ],
    }
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [
                {
                    "id": "missing-goal",
                    "group": "cập nhật trạng thái việc con",
                    "user_message": "x",
                    "dataset": "kho",
                    "expectation": {
                        "kind": "update_status",
                        "goal": "Không có",
                        "title": "Chương 1",
                        "status": "done",
                    },
                }
            ],
            {"kho": base},
        )
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [
                {
                    "id": "missing-title",
                    "group": "cập nhật trạng thái việc con",
                    "user_message": "x",
                    "dataset": "kho",
                    "expectation": {
                        "kind": "update_status",
                        "goal": "Đọc sách",
                        "title": "Không có",
                        "status": "done",
                    },
                }
            ],
            {"kho": base},
        )
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [
                {
                    "id": "missing-note-title",
                    "group": "ghi chú",
                    "user_message": "x",
                    "dataset": "kho",
                    "expectation": {
                        "kind": "set_note",
                        "goal": "Đọc sách",
                        "title": "Không có",
                        "note": "x",
                    },
                }
            ],
            {"kho": base},
        )
    with pytest.raises(LoadError):
        _suite(
            tmp_path,
            [
                {
                    "id": "missing-add-goal",
                    "group": "thêm việc con",
                    "user_message": "x",
                    "dataset": "kho",
                    "expectation": {"kind": "add_subtask", "goal": "Không có", "title": "Mới"},
                }
            ],
            {"kho": base},
        )
