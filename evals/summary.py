"""Tỉ lệ câu, luật, nhóm, số hết lượt tool, và tổng token."""

from collections.abc import Sequence
from dataclasses import dataclass

from evals.log_lines import parse_log_rows

LAW_NAMES = (
    "tool",
    "create_plan_count",
    "required",
    "prefix",
    "markdown",
    "self_name",
    "store",
)
ERROR_KINDS = frozenset(
    {
        "missing_key",
        "no_model_log",
        "ended_on_tool_log",
        "model_error",
        "bad_stop_reason",
    }
)


@dataclass(frozen=True)
class RunRecord:
    """Một lần đã phân loại, đưa vào báo cáo."""

    case_id: str
    group: str
    index: int
    kind: str
    reply: str
    lines: tuple[str, ...]
    rounds: int
    laws: dict[str, str] | None
    dataset_titles: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CaseReport:
    """Tỉ lệ của một câu."""

    id: str
    group: str
    rate: float | None
    run_errors: int
    cap_stops: int


@dataclass(frozen=True)
class RuleReport:
    """Số đạt trên số lần luật được xét."""

    name: str
    passed: int
    considered: int


@dataclass(frozen=True)
class GroupReport:
    """Tỉ lệ của một nhóm."""

    group: str
    rate: float | None
    run_errors: int
    cap_stops: int


@dataclass(frozen=True)
class Summary:
    """Báo cáo một lần chạy cả bộ."""

    input_tokens: int
    output_tokens: int
    by_case: tuple[CaseReport, ...]
    by_rule: tuple[RuleReport, ...]
    by_group: tuple[GroupReport, ...]


def _scored(runs: Sequence[RunRecord]) -> list[RunRecord]:
    return [run for run in runs if run.kind not in ERROR_KINDS]


def _rate(runs: Sequence[RunRecord]) -> float | None:
    scored = _scored(runs)
    if not scored:
        return None
    passed = sum(1 for run in scored if run.laws is not None and all(value != "fail" for value in run.laws.values()))
    return passed / len(scored)


def _tokens(runs: Sequence[RunRecord]) -> tuple[int, int]:
    incoming = 0
    outgoing = 0
    for run in runs:
        for row in parse_log_rows(run.lines):
            if "model" not in row:
                continue
            incoming += int(row["input_tokens"] or 0)
            outgoing += int(row["output_tokens"] or 0)
    return incoming, outgoing


def summarize(runs: Sequence[RunRecord]) -> Summary:
    """Tỉ lệ không dùng lần lỗi chạy và không dùng số hết lượt tool làm mẫu số."""

    order: list[str] = []
    grouped: dict[str, list[RunRecord]] = {}
    for run in runs:
        if run.case_id not in grouped:
            order.append(run.case_id)
            grouped[run.case_id] = []
        grouped[run.case_id].append(run)
    by_case = tuple(
        CaseReport(
            id=case_id,
            group=grouped[case_id][0].group,
            rate=_rate(grouped[case_id]),
            run_errors=sum(1 for run in grouped[case_id] if run.kind in ERROR_KINDS),
            cap_stops=sum(1 for run in grouped[case_id] if run.kind == "cap"),
        )
        for case_id in order
    )
    scored = _scored(runs)
    by_rule = tuple(
        RuleReport(
            name=name,
            passed=sum(1 for run in scored if run.laws is not None and run.laws.get(name) == "pass"),
            considered=sum(
                1
                for run in scored
                if run.laws is not None and run.laws.get(name) in {"pass", "fail"}
            ),
        )
        for name in LAW_NAMES
    )
    group_order: list[str] = []
    by_group_runs: dict[str, list[RunRecord]] = {}
    for run in runs:
        if run.group not in by_group_runs:
            group_order.append(run.group)
            by_group_runs[run.group] = []
        by_group_runs[run.group].append(run)
    by_group = tuple(
        GroupReport(
            group=group,
            rate=_rate(by_group_runs[group]),
            run_errors=sum(1 for run in by_group_runs[group] if run.kind in ERROR_KINDS),
            cap_stops=sum(1 for run in by_group_runs[group] if run.kind == "cap"),
        )
        for group in group_order
    )
    incoming, outgoing = _tokens(runs)
    return Summary(
        input_tokens=incoming,
        output_tokens=outgoing,
        by_case=by_case,
        by_rule=by_rule,
        by_group=by_group,
    )
