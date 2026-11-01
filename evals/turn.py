"""Chạy một câu ba lần và phân loại lần chạy theo dòng log."""

from collections.abc import Sequence
from dataclasses import dataclass

from core.llm import ModelClient
from core.plans import PlanStore
from turns.llm_turn import MissingKeyError, run_turn

from evals.log_lines import parse_log_rows
from evals.model import Case, Dataset, Expectation
from evals.score import StoreExpectation, law_results
from evals.store import build_store
from evals.summary import ERROR_KINDS

__all__ = ["ERROR_KINDS", "Outcome", "run_cases", "run_once", "_kind_of"]


@dataclass(frozen=True)
class Outcome:
    """Một lần chạy đã phân loại."""

    kind: str
    reply: str
    lines: tuple[str, ...]
    rounds: int
    laws: dict[str, str] | None


def _rounds_before(rows: list[dict[str, object]], index: int) -> int:
    rounds = 0
    cursor = 0
    while cursor < index:
        row = rows[cursor]
        if "model" in row and row.get("stop_reason") == "tool_use":
            saw_tool = False
            follower = cursor + 1
            while follower < len(rows) and "model" not in rows[follower]:
                if follower < index and "tool" in rows[follower]:
                    saw_tool = True
                follower += 1
            if saw_tool:
                rounds += 1
        cursor += 1
    return rounds


def _kind_of(lines: Sequence[str]) -> str:
    if not lines:
        return "no_model_log"
    rows = parse_log_rows(lines)
    if not any("model" in row for row in rows):
        return "no_model_log"
    last = rows[-1]
    if "tool" in last and "model" not in last:
        return "ended_on_tool_log"
    if "model" not in last:
        return "no_model_log"
    if last.get("error_type") is not None:
        return "model_error"
    rounds = _rounds_before(rows, len(rows) - 1)
    if last.get("stop_reason") == "tool_use" and rounds == 3:
        return "cap"
    if last.get("stop_reason") == "end_turn":
        return "scored"
    return "bad_stop_reason"


def _store_expectation(expectation: Expectation) -> StoreExpectation | None:
    if expectation.goal is None or expectation.title is None:
        return None
    return StoreExpectation(
        kind=expectation.kind,
        goal=expectation.goal,
        title=expectation.title,
        status=expectation.status,
        note=expectation.note,
    )


def _titles(dataset: Dataset | None) -> frozenset[str]:
    if dataset is None:
        return frozenset()
    return frozenset(item.title for plan in dataset.plans for item in plan.subtasks)


async def run_once(
    case: Case,
    store: PlanStore,
    client: ModelClient,
    api_key: str | None,
    *,
    dataset_titles: frozenset[str] = frozenset(),
) -> Outcome:
    """Một lần run_turn trên kho được truyền."""

    lines: list[str] = []
    try:
        reply = await run_turn(
            case.user_message,
            [],
            store=store,
            api_key=api_key,
            client=client,
            log=lines.append,
        )
    except MissingKeyError:
        return Outcome(kind="missing_key", reply="", lines=(), rounds=0, laws=None)
    kind = _kind_of(lines)
    rows = parse_log_rows(lines)
    rounds = _rounds_before(rows, len(rows))
    if kind in ERROR_KINDS:
        return Outcome(kind=kind, reply=reply, lines=tuple(lines), rounds=rounds, laws=None)
    laws = await law_results(
        case.group.value,
        reply,
        lines,
        store=store,
        expectation=_store_expectation(case.expectation),
        dataset_titles=dataset_titles,
    )
    return Outcome(kind=kind, reply=reply, lines=tuple(lines), rounds=rounds, laws=laws)


async def run_cases(
    cases: Sequence[Case],
    client: ModelClient,
    api_key: str | None,
    *,
    datasets: dict[str, Dataset],
) -> list[list[Outcome]]:
    """Mỗi câu ba lần. Một lỗi chạy không chặn câu sau."""

    batches: list[list[Outcome]] = []
    for case in cases:
        dataset = datasets.get(case.dataset) if case.dataset else None
        runs: list[Outcome] = []
        for _ in range(3):
            store = await build_store(dataset)
            runs.append(
                await run_once(
                    case,
                    store,
                    client,
                    api_key,
                    dataset_titles=_titles(dataset),
                )
            )
        batches.append(runs)
    return batches
