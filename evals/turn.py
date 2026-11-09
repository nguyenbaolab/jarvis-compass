"""Chạy một câu ba lần và phân loại lần chạy theo dòng log."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.llm import ModelClient, TextMessage
from core.plans import PlanStore
from turns.llm_turn import MissingKeyError, run_turn

from evals.log_lines import parse_log_rows
from evals.model import Case, Dataset, Expectation
from evals.score import StoreExpectation, law_results, store_image
from evals.store import build_store
from evals.summary import ERROR_KINDS

# Số lần mỗi câu, FR-012 spec 009.
RUNS_PER_CASE = 3
# Phải bằng _MAX_ROUNDS ở src/turns/llm_turn.py; test cap ở tests/test_eval_run.py đỏ nếu lệch.
TOOL_ROUND_CAP = 3
_V1_INSTANT = datetime(2026, 11, 6, 8, 0, tzinfo=timezone(timedelta(hours=2)))

__all__ = [
    "ERROR_KINDS",
    "RUNS_PER_CASE",
    "TOOL_ROUND_CAP",
    "Outcome",
    "run_cases",
    "run_once",
    "_kind_of",
]


@dataclass(frozen=True)
class Outcome:
    """Một lần chạy đã phân loại."""

    kind: str
    reply: str
    lines: tuple[str, ...]
    rounds: int
    laws: dict[str, str] | None
    earlier: "Outcome | None" = None
    opening: tuple[object, ...] | None = None
    after_first: tuple[object, ...] | None = None
    closing: tuple[object, ...] | None = None


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
    if last.get("stop_reason") == "tool_use" and rounds == TOOL_ROUND_CAP:
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
    cases_version: int = 1,
) -> Outcome:
    """Một ca. follow_up khác None thì hai lượt trên cùng kho và cùng mốc."""

    instant = case.instant if case.instant is not None else _V1_INSTANT
    opening = store_image(await store.list_newest_first())
    first = await _one_turn(
        case,
        store,
        client,
        api_key,
        case.user_message,
        (),
        instant,
        dataset_titles,
        cases_version,
        opening=opening,
    )
    if case.follow_up is None or first.kind in ERROR_KINDS:
        return first
    after_first = store_image(await store.list_newest_first())
    history = (
        TextMessage(role="user", text=case.user_message),
        TextMessage(role="assistant", text=first.reply),
    )
    return await _one_turn(
        case,
        store,
        client,
        api_key,
        case.follow_up,
        history,
        instant,
        dataset_titles,
        cases_version,
        opening=opening,
        after_first=after_first,
        earlier=first,
    )


async def _one_turn(
    case: Case,
    store: PlanStore,
    client: ModelClient,
    api_key: str | None,
    message: str,
    history: tuple[TextMessage, ...],
    instant: datetime,
    dataset_titles: frozenset[str],
    cases_version: int,
    *,
    opening: tuple[object, ...] | None,
    after_first: tuple[object, ...] | None = None,
    earlier: Outcome | None = None,
) -> Outcome:
    """Một lượt. Kind scored của nhóm observe trở thành observed và không chấm."""

    lines: list[str] = []
    try:
        reply = await run_turn(
            message,
            history,
            instant=instant,
            store=store,
            api_key=api_key,
            client=client,
            log=lines.append,
        )
    except MissingKeyError:
        return Outcome(kind="missing_key", reply="", lines=(), rounds=0, laws=None, opening=opening, closing=opening)
    kind = _kind_of(lines)
    rows = parse_log_rows(lines)
    rounds = _rounds_before(rows, len(rows))
    closing = store_image(await store.list_newest_first())
    if kind in ERROR_KINDS:
        return Outcome(
            kind=kind,
            reply=reply,
            lines=tuple(lines),
            rounds=rounds,
            laws=None,
            opening=opening,
            closing=closing,
        )
    if case.expectation.kind == "observe":
        shown = "observed" if kind == "scored" else kind
        return Outcome(
            kind=shown,
            reply=reply,
            lines=tuple(lines),
            rounds=rounds,
            laws=None,
            earlier=earlier,
            opening=opening,
            after_first=after_first,
            closing=closing,
        )
    closing = store_image(await store.list_newest_first())
    moves = len(getattr(store, "date_moves", ()))
    laws = await law_results(
        case.group.value,
        reply,
        lines,
        store=store,
        expectation=_store_expectation(case.expectation) if cases_version < 2 else None,
        dataset_titles=dataset_titles,
        cases_version=cases_version,
        detail=case.expectation if cases_version >= 2 else None,
        opening=opening,
        after_first=after_first,
        closing=closing,
        earlier_lines=None if earlier is None else list(earlier.lines),
        earlier_reply=None if earlier is None else earlier.reply,
        history_count=moves,
    )
    return Outcome(
        kind=kind,
        reply=reply,
        lines=tuple(lines),
        rounds=rounds,
        laws=laws,
        earlier=earlier,
        opening=opening,
        after_first=after_first,
        closing=closing,
    )


async def run_cases(
    cases: Sequence[Case],
    client: ModelClient,
    api_key: str | None,
    *,
    datasets: dict[str, Dataset],
    cases_version: int = 1,
    on_case_done: Callable[[int, int, str, tuple[str, ...]], None] | None = None,
) -> list[list[Outcome]]:
    """Mỗi câu RUNS_PER_CASE lần. Một lỗi chạy không chặn câu sau.

    Đủ lần của một câu thì gọi on_case_done nếu khác None. Câu bị ngắt giữa chừng không gọi.
    """

    batches: list[list[Outcome]] = []
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        dataset = datasets.get(case.dataset) if case.dataset else None
        runs: list[Outcome] = []
        for _ in range(RUNS_PER_CASE):
            store = await build_store(dataset)
            runs.append(
                await run_once(
                    case,
                    store,
                    client,
                    api_key,
                    dataset_titles=_titles(dataset),
                    cases_version=cases_version,
                )
            )
        batches.append(runs)
        if on_case_done is not None:
            on_case_done(index, total, case.id, tuple(item.kind for item in runs))
    return batches
