"""Báo cáo eval dựng từ file kết quả. Không gọi mô hình và không mở mạng."""

import json
from pathlib import Path

from evals.report import WRITE_COMMAND, Suite, build_report


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def test_fake_results_print_percent_average_cost_and_na(tmp_path: Path) -> None:
    """Phần trăm, token trung bình, chi phí, và rate null thành n/a."""

    results = tmp_path / "results"
    results.mkdir()
    payload = {
        "cases_version": 1,
        "scorer_version": 4,
        "prompt_version": "9",
        "definitions_version": "4",
        "model": "claude-haiku-5-5",
        "date": "2026-11-11",
        "input_tokens": 200,
        "output_tokens": 40,
        "by_case": [
            {"id": "P01", "group": "nhờ lập kế hoạch", "rate": 1.0, "run_errors": 0, "cap_stops": 0},
            {"id": "D01", "group": "xem chi tiết", "rate": None, "run_errors": 0, "cap_stops": 0},
        ],
        "by_rule": [{"name": "tool", "passed": 1, "considered": 2}],
        "by_group": [
            {"group": "nhờ lập kế hoạch", "rate": 1.0, "run_errors": 0, "cap_stops": 0},
            {"group": "xem chi tiết", "rate": None, "run_errors": 0, "cap_stops": 0},
        ],
        "runs": [
            {"id": "P01", "index": 1, "laws": {"tool": "pass"}},
            {"id": "D01", "index": 1, "laws": {"tool": "fail"}},
        ],
    }
    (results / "one.json").write_text(json.dumps(payload), encoding="utf-8")
    text = build_report(results, "NOTES\n", (Suite("v1", ("one.json",)),))
    assert (
        "| tool | The model called the expected tool or tools for the case, and no others. | 1/2 | 50.0% |"
        in text
    )
    assert "<details><summary>Exact checks for v1</summary>" in text
    assert "**tool** Passes when the calls match the group:" in text
    assert "</details>" in text
    assert "| 1/2 | 50.0% |" in text
    assert "| 2 | 200 | 40 | 100.0 | 0.000040 |" in text
    assert "| asks for plan details | xem chi tiết | 1 | n/a |" in text
    assert text.endswith("NOTES\n")


def test_committed_report_matches_results() -> None:
    """Đầu ra trên evals/results khớp docs/EVAL_REPORT.md. Lệch thì in lệnh --write."""

    root = Path(__file__).resolve().parents[1]
    golden = root / "docs" / "EVAL_REPORT.md"
    notes = _normalize((root / "docs" / "evals" / "report-notes.md").read_text(encoding="utf-8"))
    text = build_report(root / "evals" / "results", notes)
    if not golden.is_file():
        raise AssertionError(f"Thiếu file báo cáo. Chạy lại: {WRITE_COMMAND}")
    raw = golden.read_bytes()
    if b"\r\n" not in raw or b"\n" in raw.replace(b"\r\n", b""):
        raise AssertionError(f"File báo cáo không phải CRLF. Chạy lại: {WRITE_COMMAND}")
    expected = _normalize(golden.read_text(encoding="utf-8"))
    if text != expected:
        raise AssertionError(f"Bản ghi lệch file báo cáo. Chạy lại: {WRITE_COMMAND}")
