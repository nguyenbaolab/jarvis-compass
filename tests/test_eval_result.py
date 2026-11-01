"""Tỉ lệ, giấu khóa, và file kết quả. Dữ liệu ghi sẵn."""

import json
from datetime import date
from pathlib import Path

import pytest

from evals.redact import redact
from evals.result import write_result
from evals.summary import LAW_NAMES, RunRecord, summarize

_KINDS = frozenset(
    {
        "scored",
        "cap",
        "missing_key",
        "no_model_log",
        "ended_on_tool_log",
        "model_error",
        "bad_stop_reason",
    }
)
_DAY = date(2026, 1, 2)


def _laws(**overrides: str) -> dict[str, str]:
    laws = {name: "pass" for name in LAW_NAMES}
    laws["store"] = "not_applicable"
    laws.update(overrides)
    return laws


def _line(*, input_tokens: int | None, output_tokens: int | None, error_type: str | None = None) -> str:
    return json.dumps(
        {
            "model": "claude-haiku-5-5",
            "prompt_version": 1,
            "definitions_version": 1,
            "stop_reason": "end_turn",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": 1,
            "error_type": error_type,
        },
        ensure_ascii=False,
    )


def _run(
    case_id: str,
    group: str,
    index: int,
    kind: str,
    laws: dict[str, str] | None,
    lines: tuple[str, ...] = (),
) -> RunRecord:
    return RunRecord(
        case_id=case_id,
        group=group,
        index=index,
        kind=kind,
        reply="Mình nghe.",
        lines=lines,
        rounds=0,
        laws=laws,
    )


def test_case_rate_excludes_run_errors() -> None:
    """Tỉ lệ câu là số lần đạt trên số lần được chấm. Lỗi chạy không vào mẫu số."""

    runs = (
        _run("a", "chỉ kể việc", 1, "scored", _laws()),
        _run("a", "chỉ kể việc", 2, "model_error", None, (_line(input_tokens=None, output_tokens=5, error_type="TimeoutError"),)),
        _run("a", "chỉ kể việc", 3, "scored", _laws(markdown="fail"), (_line(input_tokens=2, output_tokens=3),)),
    )
    report = summarize(runs)
    case = report.by_case[0]
    assert case.rate == 0.5
    assert case.run_errors == 1
    assert case.cap_stops == 0


def test_three_run_errors_make_null_rate() -> None:
    """Ba lần lỗi chạy thì tỉ lệ null và run_errors là 3."""

    runs = tuple(
        _run("a", "chào hỏi", index, "missing_key", None)
        for index in (1, 2, 3)
    )
    case = summarize(runs).by_case[0]
    assert case.rate is None
    assert case.run_errors == 3


def test_rule_and_group_rates_and_cap() -> None:
    """Luật và nhóm tính trên lần được xét. Hết lượt tool vẫn trong tỉ lệ và được đếm riêng."""

    runs = (
        _run("a", "chỉ kể việc", 1, "scored", _laws()),
        _run("a", "chỉ kể việc", 2, "cap", _laws(markdown="fail")),
        _run("b", "chào hỏi", 1, "model_error", None),
        _run("b", "chào hỏi", 2, "model_error", None),
        _run("b", "chào hỏi", 3, "model_error", None),
    )
    report = summarize(runs)
    by_case = {item.id: item for item in report.by_case}
    assert by_case["a"].rate == 0.5
    assert by_case["a"].cap_stops == 1
    assert by_case["b"].rate is None
    assert by_case["b"].run_errors == 3
    by_group = {item.group: item for item in report.by_group}
    assert by_group["chỉ kể việc"].rate == 0.5
    assert by_group["chỉ kể việc"].cap_stops == 1
    assert by_group["chỉ kể việc"].run_errors == 0
    assert by_group["chào hỏi"].rate is None
    assert by_group["chào hỏi"].cap_stops == 0
    by_rule = {item.name: item for item in report.by_rule}
    assert by_rule["markdown"].passed == 1
    assert by_rule["markdown"].considered == 2
    assert by_rule["store"].passed == 0
    assert by_rule["store"].considered == 0
    assert by_rule["tool"].passed == 2
    assert by_rule["tool"].considered == 2


@pytest.mark.parametrize(
    "kind",
    ["missing_key", "no_model_log", "ended_on_tool_log", "model_error", "bad_stop_reason"],
)
def test_summarize_counts_each_error_kind(kind: str) -> None:
    """Mỗi mã lỗi chạy không vào mẫu số và được đếm vào run_errors theo câu và nhóm."""

    from evals.turn import ERROR_KINDS
    from evals.summary import ERROR_KINDS as SUMMARY_KINDS

    assert ERROR_KINDS is SUMMARY_KINDS
    assert kind in ERROR_KINDS
    runs = (
        _run("a", "chỉ kể việc", 1, kind, None),
        _run("a", "chỉ kể việc", 2, "scored", _laws()),
        _run("a", "chỉ kể việc", 3, "cap", _laws()),
    )
    report = summarize(runs)
    assert report.by_case[0].rate == 1.0
    assert report.by_case[0].run_errors == 1
    assert report.by_case[0].cap_stops == 1
    assert report.by_group[0].run_errors == 1
    assert report.by_group[0].rate == 1.0


def test_case_run_errors_do_not_count_cap() -> None:
    """run_errors theo câu không đếm cap."""

    runs = (
        _run("a", "chỉ kể việc", 1, "cap", _laws()),
        _run("a", "chỉ kể việc", 2, "cap", _laws()),
        _run("a", "chỉ kể việc", 3, "scored", _laws()),
    )
    case = summarize(runs).by_case[0]
    assert case.run_errors == 0
    assert case.cap_stops == 2


def test_group_rate_aggregates_runs_not_case_averages() -> None:
    """Một nhóm hai câu với số lần được chấm khác nhau: tỉ lệ nhóm gộp theo lần."""

    runs = (
        _run("a", "chỉ kể việc", 1, "scored", _laws()),
        _run("a", "chỉ kể việc", 2, "scored", _laws()),
        _run("a", "chỉ kể việc", 3, "scored", _laws()),
        _run("b", "chỉ kể việc", 1, "scored", _laws(markdown="fail")),
    )
    report = summarize(runs)
    by_case = {item.id: item for item in report.by_case}
    assert by_case["a"].rate == 1.0
    assert by_case["b"].rate == 0.0
    assert report.by_group[0].rate == 0.75


def test_write_result_creates_missing_output_directory(tmp_path: Path) -> None:
    """Thư mục ra chưa tồn tại thì write_result tạo parents rồi ghi file."""

    missing = tmp_path / "nested" / "out"
    assert not missing.exists()
    record = RunRecord(
        case_id="a",
        group="chỉ kể việc",
        index=1,
        kind="scored",
        reply="Mình nghe.",
        lines=(_eight(),),
        rounds=0,
        laws=_laws(),
    )
    path = write_result(missing, _DAY, (record,), cases_version=1, api_key="")
    assert path.is_file()
    assert path.parent == missing


def test_tokens_sum_eight_key_lines_including_errors() -> None:
    """Hai tổng cộng mọi dòng tám khóa. Trống cộng 0. Kể cả lần lỗi chạy."""

    tool_line = json.dumps(
        {
            "tool": "get_plans",
            "input": {},
            "ok": True,
            "error_type": None,
            "duration_ms": 1,
            "definitions_version": 1,
            "detail": None,
        }
    )
    runs = (
        _run(
            "a",
            "chỉ kể việc",
            1,
            "model_error",
            None,
            (_line(input_tokens=None, output_tokens=4, error_type="TimeoutError"), tool_line),
        ),
        _run("a", "chỉ kể việc", 2, "scored", _laws(), (_line(input_tokens=2, output_tokens=None),)),
    )
    report = summarize(runs)
    assert report.input_tokens == 2
    assert report.output_tokens == 4


def test_redact_replaces_nonempty_key() -> None:
    """Khóa không rỗng được thay trong câu trả lời và chuỗi log. Khóa JSON không đổi."""

    secret = "khoa-bi-mat"
    reply = f"xin {secret} nua"
    line = json.dumps({"reply": f"co {secret}", "model": "claude-haiku-5-5"}, ensure_ascii=False)
    before_keys = set(json.loads(line))
    hidden_reply, hidden_lines = redact(reply, (line,), secret)
    assert hidden_reply == "xin đã giấu khóa nua"
    assert secret not in hidden_lines[0]
    assert "đã giấu khóa" in hidden_lines[0]
    assert set(json.loads(hidden_lines[0])) == before_keys
    blank_reply, blank_lines = redact(f"giu {secret}", (line,), "   ")
    assert blank_reply == f"giu {secret}"
    assert blank_lines[0] == line
    empty_reply, empty_lines = redact(reply, (line,), "")
    assert empty_reply == reply
    assert empty_lines == (line,)


def _eight(
    *,
    model: str = "claude-haiku-5-5",
    prompt_version: int = 1,
    definitions_version: int = 1,
    stop_reason: str = "end_turn",
    error_type: str | None = None,
) -> str:
    return json.dumps(
        {
            "model": model,
            "prompt_version": prompt_version,
            "definitions_version": definitions_version,
            "stop_reason": stop_reason,
            "input_tokens": 1,
            "output_tokens": 1,
            "duration_ms": 1,
            "error_type": error_type,
        },
        ensure_ascii=False,
    )


def test_result_file_uses_passed_directory_and_date(tmp_path: Path) -> None:
    """Ghi đúng một file trong thư mục được truyền. Ngày lấy từ tham số, không phải hôm nay."""

    secret = "khoa-bi-mat"
    record = RunRecord(
        case_id="a",
        group="chỉ kể việc",
        index=1,
        kind="scored",
        reply=f"Mình nghe việc và {secret}",
        lines=(_eight(),),
        rounds=2,
        laws=_laws(),
    )
    before = set(tmp_path.iterdir())
    path = write_result(tmp_path, _DAY, (record,), cases_version=7, api_key=secret)
    created = set(tmp_path.iterdir()) - before
    assert created == {path}
    assert path.name == "p1-d1-claude-haiku-5-5-2026-01-02.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["cases_version"] == 7
    assert body["date"] == "2026-01-02"
    assert body["prompt_version"] == "1"
    assert body["definitions_version"] == "1"
    assert body["model"] == "claude-haiku-5-5"
    assert body["input_tokens"] == 1
    assert body["output_tokens"] == 1
    assert body["by_group"][0]["group"] == "chỉ kể việc"
    assert body["runs"][0]["rounds"] == 2
    assert body["runs"][0]["laws"] == _laws()
    assert isinstance(body["runs"][0]["lines"], list)
    assert len(body["runs"][0]["lines"]) == 1
    assert secret not in path.read_text(encoding="utf-8")
    assert "đã giấu khóa" in path.read_text(encoding="utf-8")
    assert "việc" in path.read_text(encoding="utf-8")
    assert body["runs"][0]["kind"] in _KINDS


def test_result_file_adds_suffix_instead_of_overwrite(tmp_path: Path) -> None:
    """File đã có thì thêm -2 rồi -3 trước .json."""

    record = RunRecord(
        case_id="a",
        group="chỉ kể việc",
        index=1,
        kind="scored",
        reply="Mình nghe.",
        lines=(_eight(model="haiku"),),
        rounds=0,
        laws=_laws(),
    )
    first = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    second = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    third = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    assert first.name == "p1-d1-haiku-2026-01-02.json"
    assert second.name == "p1-d1-haiku-2026-01-02-2.json"
    assert third.name == "p1-d1-haiku-2026-01-02-3.json"
    assert {first.name, second.name, third.name} == {
        "p1-d1-haiku-2026-01-02.json",
        "p1-d1-haiku-2026-01-02-2.json",
        "p1-d1-haiku-2026-01-02-3.json",
    }
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert second.read_text(encoding="utf-8") == third.read_text(encoding="utf-8")


def test_result_file_marks_disagreement_and_missing_log(tmp_path: Path) -> None:
    """Nhãn lệch là lech. Không có dòng tám khóa thì ba nhãn là trong."""

    mixed = (
        RunRecord("a", "chỉ kể việc", 1, "scored", "một", (_eight(prompt_version=1, model="haiku"),), 0, _laws()),
        RunRecord("a", "chỉ kể việc", 2, "scored", "hai", (_eight(prompt_version=2, model="haiku"),), 0, _laws()),
    )
    mixed_path = write_result(tmp_path, _DAY, mixed, cases_version=1, api_key="")
    mixed_body = json.loads(mixed_path.read_text(encoding="utf-8"))
    assert mixed_path.name.startswith("plech-d1-haiku-")
    assert mixed_body["prompt_version"] == "lech"
    assert mixed_body["definitions_version"] == "1"
    assert mixed_body["model"] == "haiku"
    assert "prompt_version" in mixed_body["runs"][0]["lines"][0]
    empty = (
        RunRecord("b", "chào hỏi", 1, "no_model_log", "", (), 0, None),
    )
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty_path = write_result(empty_dir, _DAY, empty, cases_version=1, api_key="")
    empty_body = json.loads(empty_path.read_text(encoding="utf-8"))
    assert empty_path.name == "ptrong-dtrong-trong-2026-01-02.json"
    assert empty_body["prompt_version"] == "trong"
    assert empty_body["definitions_version"] == "trong"
    assert empty_body["model"] == "trong"


def test_result_file_stores_each_kind(tmp_path: Path) -> None:
    """kind của từng lần là một mã trong tập đã khóa."""

    runs = tuple(
        RunRecord("a", "chỉ kể việc", index, kind, "Mình nghe.", (_eight(),) if kind != "no_model_log" else (), index, _laws() if kind in {"scored", "cap"} else None)
        for index, kind in enumerate(sorted(_KINDS), start=1)
    )
    path = write_result(tmp_path, _DAY, runs, cases_version=1, api_key="")
    body = json.loads(path.read_text(encoding="utf-8"))
    assert {item["kind"] for item in body["runs"]} == _KINDS


def _create_plan_line(subtasks: list[str]) -> str:
    return json.dumps(
        {
            "tool": "create_plan",
            "input": {"goal": "Đọc", "subtasks": subtasks},
            "ok": True,
            "error_type": None,
            "duration_ms": 1,
            "definitions_version": 1,
            "detail": None,
        },
        ensure_ascii=False,
    )


def test_manual_titles_two_new_titles_make_two_slots(tmp_path: Path) -> None:
    """US6-1: hai tiêu đề mới thành hai ô đánh dấu."""

    record = RunRecord(
        case_id="a",
        group="nhờ lập kế hoạch",
        index=1,
        kind="scored",
        reply="Mình nghe.",
        lines=(_eight(), _create_plan_line(["Ngày 1: họp", "Tuần 2: nộp"])),
        rounds=1,
        laws=_laws(prefix="fail"),
    )
    path = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["runs"][0]["manual_titles"] == [
        {"title": "Ngày 1: họp", "mark": "unmarked"},
        {"title": "Tuần 2: nộp", "mark": "unmarked"},
    ]


def test_manual_titles_empty_when_no_new_title(tmp_path: Path) -> None:
    """US6-2: không tiêu đề mới thì không có ô đánh dấu."""

    record = RunRecord(
        case_id="a",
        group="chỉ kể việc",
        index=1,
        kind="scored",
        reply="Mình nghe.",
        lines=(_eight(),),
        rounds=0,
        laws=_laws(),
    )
    path = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["runs"][0]["manual_titles"] == []
    error = RunRecord(
        case_id="b",
        group="chỉ kể việc",
        index=1,
        kind="model_error",
        reply="",
        lines=(_eight(error_type="TimeoutError"),),
        rounds=0,
        laws=None,
    )
    error_path = write_result(tmp_path / "err", _DAY, (error,), cases_version=1, api_key="")
    assert json.loads(error_path.read_text(encoding="utf-8"))["runs"][0]["manual_titles"] == []


def test_manual_titles_start_unmarked_and_do_not_change_rate(tmp_path: Path) -> None:
    """US6-3: mark ban đầu unmarked. Ghi mark vào file, đọc lại, tỉ lệ không đổi."""

    record = RunRecord(
        case_id="a",
        group="nhờ lập kế hoạch",
        index=1,
        kind="scored",
        reply="Mình nghe.",
        lines=(_eight(), _create_plan_line(["Ngày 1: họp", "Đọc sách"])),
        rounds=1,
        laws=_laws(prefix="fail"),
        dataset_titles=frozenset({"Đọc sách"}),
    )
    path = write_result(tmp_path, _DAY, (record,), cases_version=1, api_key="")
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["runs"][0]["manual_titles"] == [{"title": "Ngày 1: họp", "mark": "unmarked"}]
    rate_before = body["by_case"][0]["rate"]
    assert rate_before == summarize((record,)).by_case[0].rate
    body["runs"][0]["manual_titles"][0]["mark"] = "fail"
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reread = json.loads(path.read_text(encoding="utf-8"))
    assert reread["runs"][0]["manual_titles"][0]["mark"] == "fail"
    assert reread["by_case"][0]["rate"] == rate_before
    assert {item["name"] for item in reread["by_rule"]} == set(LAW_NAMES)


def test_redact_nested_tool_and_model_lines() -> None:
    """Giấu khóa trong input lồng hai tầng, detail, và dòng tám khóa. Thứ tự khóa JSON giữ nguyên."""

    secret = "khoa-bi-mat"
    eight_keys = (
        "model",
        "prompt_version",
        "definitions_version",
        "stop_reason",
        "input_tokens",
        "output_tokens",
        "duration_ms",
        "error_type",
    )
    seven_keys = (
        "tool",
        "input",
        "ok",
        "error_type",
        "duration_ms",
        "definitions_version",
        "detail",
    )
    eight = json.dumps(
        {
            "model": f"m-{secret}",
            "prompt_version": 1,
            "definitions_version": 1,
            "stop_reason": "end_turn",
            "input_tokens": 1,
            "output_tokens": 1,
            "duration_ms": 1,
            "error_type": None,
        },
        ensure_ascii=False,
    )
    seven = json.dumps(
        {
            "tool": "update_subtask",
            "input": {"outer": {"inner": f"co {secret}"}},
            "ok": True,
            "error_type": None,
            "duration_ms": 1,
            "definitions_version": 1,
            "detail": f"loi {secret}",
        },
        ensure_ascii=False,
    )
    _, hidden = redact("ok", (eight, seven), secret)
    eight_body = json.loads(hidden[0])
    seven_body = json.loads(hidden[1])
    assert list(eight_body) == list(eight_keys)
    assert list(seven_body) == list(seven_keys)
    assert secret not in hidden[0]
    assert secret not in hidden[1]
    assert "đã giấu khóa" in eight_body["model"]
    assert "đã giấu khóa" in seven_body["input"]["outer"]["inner"]
    assert "đã giấu khóa" in seven_body["detail"]
