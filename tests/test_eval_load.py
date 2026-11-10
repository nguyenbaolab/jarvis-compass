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


def test_absent_new_keys_are_none(tmp_path: Path) -> None:
    """Khóa mới vắng thì None. File v1 không phải viết lại."""

    suite = _suite(tmp_path, [_case("chỉ kể việc", "no_tool")])
    case = suite.cases[0]
    assert case.instant is None
    assert case.follow_up is None
    assert suite.datasets == {}


def test_reads_instant_follow_up_date_effort_priority(tmp_path: Path) -> None:
    """Bộ v2 đọc mốc, tin thứ hai, ngày, sức và ưu tiên."""

    cases_path = tmp_path / "cases.json"
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    _write(
        data_dir / "kho.json",
        {
            "name": "kho",
            "plans": [
                {
                    "goal": "Đọc sách",
                    "priority": "high",
                    "subtasks": [
                        {
                            "title": "Chương 1",
                            "status": "pending",
                            "note": None,
                            "scheduled_on": "2026-11-11",
                            "effort": "S",
                        }
                    ],
                }
            ],
        },
    )
    _write(
        cases_path,
        {
            "cases_version": 2,
            "cases": [
                {
                    "id": "V",
                    "group": "ghi nhận",
                    "instant": "2026-11-11T10:00:00+02:00",
                    "follow_up": "tiếp",
                    "user_message": "một câu",
                    "dataset": "kho",
                    "expectation": {"kind": "observe"},
                }
            ],
        },
    )
    suite = load_suite(cases_path, data_dir)
    case = suite.cases[0]
    assert case.instant is not None
    assert case.instant.tzinfo is not None
    assert case.follow_up == "tiếp"
    plan = suite.datasets["kho"].plans[0]
    assert plan.priority == "high"
    assert plan.subtasks[0].scheduled_on == "2026-11-11"
    assert plan.subtasks[0].effort == "S"


def test_v2_file_has_seventeen_cases() -> None:
    """File v2 đúng mười bảy id và mỗi ca có mốc."""

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    assert suite.cases_version == 2
    assert [case.id for case in suite.cases] == [f"V2-{index:02d}" for index in range(1, 18)]
    assert all(case.instant is not None for case in suite.cases)


def test_v2_priority_and_effort_cases_load() -> None:
    """V2-15 đến V2-17 đọc priority, goal và effort."""

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    by_id = {case.id: case for case in suite.cases}
    assert by_id["V2-15"].expectation.kind == "create_with_priority"
    assert by_id["V2-15"].expectation.priority == "high"
    assert by_id["V2-16"].expectation.kind == "set_priority_existing"
    assert by_id["V2-16"].expectation.goal == "Chạy được 10km"
    assert by_id["V2-16"].expectation.priority == "low"
    assert by_id["V2-17"].expectation.kind == "set_effort_existing"
    assert by_id["V2-17"].expectation.title == "Chạy 10km không nghỉ"
    assert by_id["V2-17"].expectation.effort == "L"


def test_v2_case_without_instant_is_rejected(tmp_path: Path) -> None:
    """Bộ v2 thiếu instant thì từ chối."""

    cases_path = tmp_path / "cases.json"
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    _write(
        cases_path,
        {
            "cases_version": 2,
            "cases": [
                {
                    "id": "V",
                    "group": "hạn tương đối: hỏi lại",
                    "user_message": "một câu",
                    "dataset": "",
                    "expectation": {"kind": "ask_back_no_write"},
                }
            ],
        },
    )
    with pytest.raises(LoadError):
        load_suite(cases_path, data_dir)


def test_v2_missing_required_field_is_rejected(tmp_path: Path) -> None:
    """Thiếu deadline của loại create_with_deadline thì từ chối."""

    cases_path = tmp_path / "cases.json"
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    _write(
        cases_path,
        {
            "cases_version": 2,
            "cases": [
                {
                    "id": "V",
                    "group": "hạn tương đối: lưu ngày",
                    "instant": "2026-11-11T10:00:00+02:00",
                    "user_message": "một câu",
                    "dataset": "",
                    "expectation": {"kind": "create_with_deadline"},
                }
            ],
        },
    )
    with pytest.raises(LoadError):
        load_suite(cases_path, data_dir)


def test_v2_unknown_goal_or_title_is_rejected(tmp_path: Path) -> None:
    """Goal hoặc tiêu đề không có trong bộ dữ liệu thì từ chối."""

    cases_path = tmp_path / "cases.json"
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    _write(
        data_dir / "kho.json",
        {
            "name": "kho",
            "plans": [
                {
                    "goal": "Đọc sách",
                    "subtasks": [{"title": "Chương 1", "status": "pending", "note": None}],
                }
            ],
        },
    )
    _write(
        cases_path,
        {
            "cases_version": 2,
            "cases": [
                {
                    "id": "V",
                    "group": "dời ngày không cần xác nhận",
                    "instant": "2026-11-11T10:00:00+02:00",
                    "user_message": "một câu",
                    "dataset": "kho",
                    "expectation": {
                        "kind": "reschedule_no_confirm",
                        "goal": "Không có",
                        "dates": [["Chương 1", "2026-11-12"]],
                        "history_moves": 1,
                    },
                }
            ],
        },
    )
    with pytest.raises(LoadError):
        load_suite(cases_path, data_dir)


def test_v2_instants_have_expected_weekdays() -> None:
    """V2-01 đến V2-08 đúng thứ của mốc trong mục 10a."""

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    by_id = {case.id: case for case in suite.cases}
    wednesday = {"V2-01", "V2-03", "V2-04", "V2-05", "V2-06", "V2-07", "V2-08"}
    for case_id in wednesday:
        instant = by_id[case_id].instant
        assert instant is not None
        assert instant.date().isoformat() == "2026-11-11"
        assert instant.date().weekday() == 2
    friday = by_id["V2-02"].instant
    assert friday is not None
    assert friday.date().isoformat() == "2026-11-13"
    assert friday.date().weekday() == 4


def test_v2_relative_deadline_groups() -> None:
    """Nhóm hỏi lại chỉ còn V2-02. Nhóm lưu ngày gồm V2-01, V2-03, V2-04, V2-05."""

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    by_id = {case.id: case for case in suite.cases}
    ask = {case.id for case in suite.cases if case.group == "hạn tương đối: hỏi lại"}
    save = {case.id for case in suite.cases if case.group == "hạn tương đối: lưu ngày"}
    assert ask == {"V2-02"}
    assert save == {"V2-01", "V2-03", "V2-04", "V2-05"}
    assert by_id["V2-03"].expectation.kind == "create_with_deadline"
    assert by_id["V2-04"].user_message == "Lập kế hoạch giúp mình ôn thi giải tích, hạn là thứ Hai."


def test_v2_expected_dates_follow_the_rules() -> None:
    """Deadline V2-01, V2-03, V2-04 và V2-05 khớp luật hạn tương đối tính từ instant của ca."""

    from datetime import timedelta

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    by_id = {case.id: case for case in suite.cases}

    def sunday(day: object) -> object:
        return day + timedelta(days=(6 - day.weekday()))

    def sunday_of_next_week(day: object) -> object:
        return sunday(day) + timedelta(days=7)

    def next_monday(day: object) -> object:
        ahead = (0 - day.weekday()) % 7
        return day + timedelta(days=ahead or 7)

    def friday_of_next_week(day: object) -> object:
        monday = day - timedelta(days=day.weekday())
        return monday + timedelta(days=11)

    first = by_id["V2-01"]
    third = by_id["V2-03"]
    fourth = by_id["V2-04"]
    fifth = by_id["V2-05"]
    assert first.instant is not None and third.instant is not None
    assert fourth.instant is not None and fifth.instant is not None
    assert first.expectation.deadline == sunday(first.instant.date()).isoformat()
    assert third.expectation.deadline == sunday_of_next_week(third.instant.date()).isoformat()
    assert fourth.expectation.deadline == next_monday(fourth.instant.date()).isoformat()
    assert fifth.expectation.deadline == friday_of_next_week(fifth.instant.date()).isoformat()


def test_v3_file_has_eight_cases() -> None:
    """File v3 đúng tám id, mỗi ca có mốc, ca 7 và ca 8 có câu lượt sau."""

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v3.json", root / "evals" / "datasets")
    assert suite.cases_version == 3
    assert [case.id for case in suite.cases] == [f"V3-{index:02d}" for index in range(1, 9)]
    assert all(case.instant is not None for case in suite.cases)
    by_id = {case.id: case for case in suite.cases}
    assert by_id["V3-07"].follow_up == "Ừ, ghi và dời như vậy."
    assert by_id["V3-07"].dataset == "qua_tai"
    assert by_id["V3-08"].follow_up == "Thôi không thêm nữa."
    assert {plan.goal for plan in suite.datasets["qua_tai"].plans} >= {"Một", "Nộp", "Đầy"}
