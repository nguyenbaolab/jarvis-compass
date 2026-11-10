"""Sinh docs/EVAL_REPORT.md từ danh sách file kết quả tường minh. Chỉ thư viện chuẩn."""

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

INPUT_USD_PER_MTOK = 0.10
OUTPUT_USD_PER_MTOK = 0.50

WRITE_COMMAND = "PYTHONPATH=src uv run python -m evals.report --write docs/EVAL_REPORT.md"

_LAW_ORDER = (
    "tool",
    "create_plan_count",
    "required",
    "prefix",
    "markdown",
    "self_name",
    "store",
)

_V1 = (
    "p3-d2-claude-haiku-5-5-2026-11-08.json",
    "p7-d3-claude-haiku-5-5-2026-11-09.json",
    "p9-d4-claude-haiku-5-5-2026-11-10-2.json",
    "p9-d4-claude-haiku-5-5-2026-11-11.json",
)
_V2 = (
    "p4-d3-claude-haiku-5-5-2026-11-09-2.json",
    "p5-d3-claude-haiku-5-5-2026-11-09-2.json",
    "p6-d3-claude-haiku-5-5-2026-11-09-2.json",
    "p7-d3-claude-haiku-5-5-2026-11-09-2.json",
    "p8-d4-claude-haiku-5-5-2026-11-10-2.json",
    "p9-d4-claude-haiku-5-5-2026-11-10-3.json",
)
_V3 = (
    "p8-d4-claude-haiku-5-5-2026-11-10-3.json",
    "p9-d4-claude-haiku-5-5-2026-11-10.json",
    "p9-d4-claude-haiku-5-5-2026-11-10-4.json",
)

_GROUP_ENGLISH = {
    "nhờ lập kế hoạch": "asks for a plan",
    "chỉ kể việc": "only mentions tasks",
    "hỏi danh sách": "asks for the plan list",
    "xem chi tiết": "asks for plan details",
    "cập nhật trạng thái việc con": "updates a task status",
    "thêm việc con": "adds a task",
    "ghi chú": "sets a note",
    "chào hỏi": "greeting",
    "câu mơ hồ": "ambiguous request",
    "câu ngoài phạm vi": "out of scope",
    "hạn tương đối: lưu ngày": "relative deadline stored as a date",
    "hạn tương đối: hỏi lại": "relative deadline, asks back",
    "hạn cả kế hoạch": "whole-plan deadline",
    "dời hạn trùng": "reschedule into a clashing deadline",
    "dời ngày không cần xác nhận": "reschedule without confirmation",
    "tin dài có ngày": "long message with dates",
    "liệt kê tiêu đề": "listed titles kept verbatim",
    "nhóm việc mơ hồ": "ambiguous task group",
    "ghi nhận": "recorded only, not scored",
    "ưu tiên do người dùng nêu": "priority stated by the user",
    "đặt ưu tiên": "set priority",
    "đặt sức": "set effort",
    "quét tải: trong quỹ": "within budget",
    "quét tải: vượt quỹ": "over budget",
    "quét tải: việc xong": "done and skipped tasks ignored",
    "quét tải: sức": "effort hours",
    "quét tải: câu cảnh báo": "warning wording",
    "quét tải: thứ tự dời": "order of proposed moves",
    "quét tải: xác nhận": "confirm turn",
    "quét tải: từ chối": "refusal",
}

_RULE_SUMMARY = {
    "tool": "The model called the expected tool or tools for the case, and no others.",
    "create_plan_count": "A plan was created exactly when the case asks for one.",
    "required": "Every tool call carries all of its required arguments.",
    "prefix": "New task titles carry no ordering prefix such as 'Day 1:'.",
    "markdown": "The reply is plain text, with no code fences, bold text or headings.",
    "self_name": "The reply does not describe the assistant as a separate planning assistant (one persona, D-002).",
    "store": "The saved plans end in the state the case expects.",
}

# Mô tả đầy đủ từng luật, đúng nhánh cases_version trong evals/score.py.
_RULE_TEXT = {
    1: {
        "tool": (
            "Passes when the calls match the group: none for the four no-tool groups; "
            "exactly one create_plan for a plan request; one or more get_plans calls for a list request; "
            "one or more calls that are only get_plans or get_plan_detail for a details request; "
            "and, for a write group, only get_plans, get_plan_detail, and that group's write tool, "
            "including no calls at all. Any other group fails."
        ),
        "create_plan_count": (
            "Passes when create_plan is called once for a plan request and zero times for every other group."
        ),
        "required": (
            "Passes when every tool call names a catalog tool and the input object contains every required schema key. "
            "A turn with no tool call passes."
        ),
        "prefix": (
            "Passes when no new task title, after Unicode NFC, casefold, and stripping leading spaces, "
            "starts with ngày, tuần, bước, or giai đoạn plus a number, or with digits and a dot. "
            "Titles already in the dataset are not new."
        ),
        "markdown": (
            "Fails if the reply contains a code fence, a backtick, **, __, or ](, "
            "or a line whose leading spaces are followed by # or '* '."
        ),
        "self_name": "Fails if the reply contains trợ lý lập kế hoạch after Unicode NFC.",
        "store": (
            "Not applicable except for a status update, an added task, or a note. "
            "Those pass when the saved plan has the expected new task, status, or note, "
            "and fail when the store or the expectation is missing."
        ),
    },
    2: {
        "tool": (
            "By case kind: a create kind must call exactly create_plan; ask-back may call only get_plans and get_plan_detail; "
            "an existing deadline must call reschedule_subtasks and may also call those two reads; "
            "a reschedule without confirmation must do that with confirm not set true; "
            "a clash must do that on the first turn and call reschedule_subtasks with confirm true on the second; "
            "observe is not applicable; priority and effort must call set_plan_priority or set_subtask_effort "
            "and nothing outside that tool plus the two reads. Any other kind fails."
        ),
        "create_plan_count": (
            "Passes when create_plan occurs once for a create kind and zero times otherwise, "
            "counting calls on the earlier turn and this turn."
        ),
        "required": "Same required-key check as v1, over tool calls from the earlier turn and this turn.",
        "prefix": "Same new-title prefix check as v1, over titles created on the earlier turn and this turn.",
        "markdown": "Passes when every reply in the turn pair passes the v1 markdown check.",
        "self_name": "Passes when every reply in the turn pair passes the v1 self-name check.",
        "store": (
            "Observe is not applicable. Ask-back passes when the store and the date-history count are unchanged. "
            "A new deadline passes when the latest pending date and the last pending task's date equal the deadline "
            "and priority and effort are unset. An existing deadline passes when goals and titles stay, "
            "only the last pending date on that plan becomes the deadline, and other plans' dates stay. "
            "A reschedule passes when the named plan's dates match and the history count matches, "
            "and other plans stay unchanged; a clash also requires the store after turn one to equal the opening store "
            "and the other plan to stay unchanged. A long message passes when the goal is one line under 80 characters "
            "with no date or time mark, no task title has a date mark, and priority and effort are unset. "
            "Verbatim titles pass when each expected title is present after NFC and stripping, with priority and effort unset. "
            "Priority and effort cases pass when only that field changes to the expected value."
        ),
    },
    3: {
        "tool": (
            "Fails if any call is outside get_plans, get_plan_detail, add_subtask, create_plan, and reschedule_subtasks. "
            "Within budget and done-or-skipped pass when add_subtask was called and the reply does not contain "
            "Lần này chưa ghi. Over budget passes when add_subtask or create_plan was called and the reply asks a question "
            "without Đã thêm, Đã ghi, Đã tạo, or Đã lưu, repeats each hour number from the expectation, "
            "and, when the expectation contains tính tạm, includes one of tính tạm, ước tính, tạm tính, ước lượng, "
            "or chưa có sức. Effort and the warning sentence pass when create_plan was called and the reply meets that check; "
            "the warning sentence also fails when the reply contains sang followed by a numeric day and month. "
            "Move order passes when add_subtask was called, the reply meets that check, and each expected title is followed "
            "by its DD/MM with no third numbered item. Confirm passes when this turn has a confirmed add_subtask "
            "whose load_moves list is non-empty, reschedule_subtasks is absent, the first turn sets no confirm true, "
            "and the first reply asks rather than claims a write. Refusal passes when the first turn called add_subtask "
            "and that reply asks rather than claims a write. Any other kind fails."
        ),
        "create_plan_count": (
            "Passes when create_plan occurs once for the effort and warning cases and zero times otherwise, "
            "counting both turns."
        ),
        "required": "Same required-key check as v1, over tool calls from the earlier turn and this turn.",
        "prefix": "Same new-title prefix check as v1, over titles created on the earlier turn and this turn.",
        "markdown": "Passes when every reply in the turn pair passes the v1 markdown check.",
        "self_name": "Passes when every reply in the turn pair passes the v1 self-name check.",
        "store": (
            "Refusal passes when the closing store equals the opening store. "
            "Over budget, effort, the warning sentence, and move order pass when the store is unchanged "
            "and the date-history count is zero. Within budget and done-or-skipped pass when the named plan's dates match, "
            "other plans are unchanged, and the history count is zero. "
            "Confirm passes when the store after turn one still equals the opening store, the history count equals the expectation, "
            "the named plan's dates match, and the other plan is unchanged. "
            "This check does not read the confirm flag. A missing image fails."
        ),
    },
}


@dataclass(frozen=True)
class Suite:
    """Một bộ câu và các file kết quả, file cuối là bản chung cuộc."""

    name: str
    files: tuple[str, ...]


SUITES = (
    Suite("v1", _V1),
    Suite("v2", _V2),
    Suite("v3", _V3),
)


def _unix(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_cell(item) for item in row) + " |" for row in rows]
    return "\n".join((head, rule, *body))


def _load(directory: Path, name: str) -> dict[str, object]:
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Thiếu file kết quả đã liệt kê: {name}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"File kết quả không phải object: {name}")
    return loaded


def _int(body: dict[str, object], key: str) -> int:
    value = body[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Trường {key} không phải số nguyên.")
    return value


def _percent(passed: int, considered: int) -> str:
    if considered == 0:
        return "n/a"
    return f"{100.0 * passed / considered:.1f}%"


def _rate(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{float(value):.2f}"


def _rule_items(body: dict[str, object]) -> list[tuple[str, int, int]]:
    raw = body.get("by_rule")
    if not isinstance(raw, list):
        raise ValueError("by_rule không phải danh sách.")
    items: list[tuple[str, int, int]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Một dòng luật không phải object.")
        name = str(item.get("name"))
        passed = item.get("passed")
        considered = item.get("considered")
        if isinstance(passed, bool) or not isinstance(passed, int):
            raise ValueError(f"passed của {name} không phải số nguyên.")
        if isinstance(considered, bool) or not isinstance(considered, int):
            raise ValueError(f"considered của {name} không phải số nguyên.")
        items.append((name, passed, considered))
    return items


def _full_check(version: object, name: str) -> str:
    texts = _RULE_TEXT.get(version) if isinstance(version, int) else None
    if texts is None:
        return "No one-line description is recorded for this cases_version."
    return texts.get(name, "This name is not one of the seven laws described from score.py.")


def _rule_rows(body: dict[str, object]) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for name, passed, considered in _rule_items(body):
        summary = _RULE_SUMMARY.get(name, _full_check(body.get("cases_version"), name))
        rows.append((name, summary, f"{passed}/{considered}", _percent(passed, considered)))
    return rows


def _exact_checks(suite_name: str, body: dict[str, object]) -> str:
    """Khối details dưới bảng luật. Chữ mô tả là bản đầy đủ của nhánh chấm."""

    version = body.get("cases_version")
    lines = [f"<details><summary>Exact checks for {suite_name}</summary>", ""]
    for name, _passed, _considered in _rule_items(body):
        lines.append(f"**{name}** {_full_check(version, name)}")
        lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def _case_counts(body: dict[str, object]) -> dict[str, int]:
    raw = body.get("by_case")
    if not isinstance(raw, list):
        raise ValueError("by_case không phải danh sách.")
    counts: dict[str, int] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Một dòng ca không phải object.")
        group = str(item.get("group"))
        counts[group] = counts.get(group, 0) + 1
    return counts


def _group_rows(body: dict[str, object]) -> list[tuple[object, ...]]:
    raw = body.get("by_group")
    if not isinstance(raw, list):
        raise ValueError("by_group không phải danh sách.")
    counts = _case_counts(body)
    rows: list[tuple[object, ...]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Một dòng nhóm không phải object.")
        group = str(item.get("group"))
        english = _GROUP_ENGLISH.get(group, group)
        rows.append((english, group, counts.get(group, 0), _rate(item.get("rate"))))
    return rows


def _runs(body: dict[str, object]) -> list[dict[str, object]]:
    raw = body.get("runs")
    if not isinstance(raw, list):
        raise ValueError("runs không phải danh sách.")
    return [item for item in raw if isinstance(item, dict)]


def _passed_cells(body: dict[str, object]) -> tuple[str, ...]:
    raw = body.get("by_rule")
    found: dict[str, str] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name"))
            passed = item.get("passed")
            considered = item.get("considered")
            if isinstance(passed, int) and not isinstance(passed, bool) and isinstance(considered, int):
                found[name] = f"{passed}/{considered}"
    return tuple(found.get(name, "n/a") for name in _LAW_ORDER)


def _failed_rows(suite: str, body: dict[str, object]) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for run in _runs(body):
        laws = run.get("laws")
        if not isinstance(laws, dict):
            continue
        failed = [name for name in _LAW_ORDER if laws.get(name) == "fail"]
        failed.extend(
            str(name)
            for name, value in laws.items()
            if value == "fail" and str(name) not in failed
        )
        if not failed:
            continue
        rows.append((suite, run.get("id"), run.get("index"), ", ".join(failed)))
    return rows


def _cost(incoming: int, outgoing: int) -> str:
    usd = incoming / 1_000_000 * INPUT_USD_PER_MTOK + outgoing / 1_000_000 * OUTPUT_USD_PER_MTOK
    return f"{usd:.6f}"


def _average(total: int, turns: int) -> str:
    if turns == 0:
        return "n/a"
    return f"{total / turns:.1f}"


def build_report(results_dir: Path, notes: str, suites: tuple[Suite, ...] = SUITES) -> str:
    """Dựng báo cáo tiếng Anh. notes được nối nguyên văn ở cuối."""

    loaded = {
        name: _load(results_dir, name)
        for suite in suites
        for name in suite.files
    }
    parts = [
        "# Compass eval report",
        "",
        "## How this report is produced",
        "",
        "The tables in this file are generated by `evals/report.py` from result files in `evals/results`. "
        "The script does not choose files by pattern. Each suite names its files in order, "
        "and the last file of a suite is that suite's final run.",
        "",
        "Recreate this file from the repository root:",
        "",
        "```",
        WRITE_COMMAND,
        "```",
        "",
        "Check a written copy with `--check docs/EVAL_REPORT.md`. "
        "The command prints a diff and exits 1 when the file differs.",
        "",
        "## Final results",
        "",
        "Each rule row uses a fixed one-sentence summary. "
        "The exact checks from the current `cases_version` branch in `evals/score.py` are in the details block under the table. "
        "Passed and considered counts, and group rates, are copied from the final result file. "
        "A group rate of null is printed as n/a. A rule with nothing considered is n/a.",
    ]
    for suite in suites:
        final_name = suite.files[-1]
        body = loaded[final_name]
        parts.extend(
            [
                "",
                f"### {suite.name}",
                "",
                f"Final file: `{final_name}`. "
                f"Date {body.get('date')}, prompt {body.get('prompt_version')}, "
                f"definitions {body.get('definitions_version')}, scorer {body.get('scorer_version')}.",
                "",
                _table(("Rule", "What the scorer checks", "Passed", "Percent"), _rule_rows(body)),
                "",
                _exact_checks(suite.name, body),
                "",
                _table(("English", "Group", "Cases", "Rate"), _group_rows(body)),
            ]
        )
    round_rows: list[tuple[object, ...]] = []
    for suite in suites:
        for name in suite.files:
            body = loaded[name]
            turns = len(_runs(body))
            round_rows.append(
                (
                    suite.name,
                    name,
                    body.get("date"),
                    body.get("prompt_version"),
                    body.get("definitions_version"),
                    body.get("scorer_version"),
                    turns,
                    _int(body, "input_tokens"),
                    _int(body, "output_tokens"),
                    *_passed_cells(body),
                )
            )
    parts.extend(
        [
            "",
            "## Rounds",
            "",
            "One row per listed result file. Passed columns are passed/considered for that file.",
            "",
            _table(
                (
                    "Suite",
                    "File",
                    "Date",
                    "Prompt",
                    "Definitions",
                    "Scorer",
                    "Runs",
                    "Input tokens",
                    "Output tokens",
                    *_LAW_ORDER,
                ),
                round_rows,
            ),
            "",
            "## Failed runs",
            "",
            "Runs in the three final files whose laws include at least one fail. "
            "not_applicable is not a failure.",
        ]
    )
    for suite in suites:
        body = loaded[suite.files[-1]]
        failed = _failed_rows(suite.name, body)
        parts.extend(["", f"### {suite.name}", ""])
        if not failed:
            parts.append("none")
            continue
        parts.append(_table(("Suite", "Case", "Run", "Failed laws"), failed))
    cost_rows: list[tuple[object, ...]] = []
    for suite in suites:
        name = suite.files[-1]
        body = loaded[name]
        incoming = _int(body, "input_tokens")
        outgoing = _int(body, "output_tokens")
        turns = len(_runs(body))
        cost_rows.append(
            (
                suite.name,
                name,
                turns,
                incoming,
                outgoing,
                _average(incoming, turns),
                _cost(incoming, outgoing),
            )
        )
    parts.extend(
        [
            "",
            "## Tokens and cost",
            "",
            "Figures are the final run of each suite. "
            f"Estimated USD uses INPUT_USD_PER_MTOK = {INPUT_USD_PER_MTOK:.2f} and "
            f"OUTPUT_USD_PER_MTOK = {OUTPUT_USD_PER_MTOK:.2f}, "
            "the prices recorded in docs/PRODUCT.md section 5, and is rounded to 6 decimal places. "
            "This is an estimate from token counts, not an invoice. "
            "Average input is input tokens divided by the number of runs.",
            "",
            _table(
                (
                    "Suite",
                    "File",
                    "Runs",
                    "Input tokens",
                    "Output tokens",
                    "Average input per run",
                    "Estimated USD",
                ),
                cost_rows,
            ),
        ]
    )
    generated = "\n".join(parts).rstrip("\n")
    note_text = _unix(notes).strip("\n")
    return generated + "\n\n" + note_text + "\n"


def write_crlf(path: Path, text: str) -> None:
    body = _unix(text)
    if not body.endswith("\n"):
        body += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.replace("\n", "\r\n").encode("utf-8"))


def check_report(path: Path, text: str) -> str | None:
    """Trả diff khi lệch. None khi file đã ghi khớp đầu ra."""

    if not path.is_file():
        return f"Thiếu {path}. Chạy lại: {WRITE_COMMAND}\n"
    current = _unix(path.read_text(encoding="utf-8"))
    if current == text:
        return None
    diff = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile=str(path),
            tofile="report",
        )
    )
    return f"Bản ghi lệch file đã có. Chạy lại: {WRITE_COMMAND}\n{diff}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    if args.write is not None and args.check is not None:
        print("Chỉ dùng một trong --write và --check.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    notes_path = root / "docs" / "evals" / "report-notes.md"
    notes = notes_path.read_text(encoding="utf-8")
    text = build_report(root / "evals" / "results", notes)
    if args.write is not None:
        write_crlf(args.write, text)
        return 0
    if args.check is not None:
        diff = check_report(args.check, text)
        if diff is None:
            return 0
        sys.stdout.write(diff)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
