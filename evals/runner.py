"""Lệnh chạy tay. Chỉ main đọc môi trường và dựng AnthropicModel."""

import asyncio
import os
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from core.llm import ModelClient

from evals.load import LoadError, load_suite
from evals.model import Suite
from evals.result import write_result
from evals.summary import RunRecord, summarize
from evals.turn import Outcome, run_cases

_KEY = "JARVIS_EVAL_ANTHROPIC_KEY"
_MISSING = "Thiếu JARVIS_EVAL_ANTHROPIC_KEY."


def check_key(env: Mapping[str, str], client: ModelClient) -> str | None:
    """Đọc khóa từ mapping. Thiếu, rỗng, hoặc chỉ khoảng trắng thì in stderr và trả None.

    Khóa trả về đã strip, dùng cho lượt và cho việc giấu khóa.
    """

    del client
    key = env.get(_KEY)
    if key is None or key.strip() == "":
        print(_MISSING, file=sys.stderr)
        return None
    return key.strip()


def stop_interrupted(env: Mapping[str, str], client: ModelClient) -> int:
    """Dừng cả bộ. Không ghi file."""

    del env, client
    return 130


def _titles(suite: Suite, dataset_name: str) -> frozenset[str]:
    dataset = suite.datasets.get(dataset_name) if dataset_name else None
    if dataset is None:
        return frozenset()
    return frozenset(item.title for plan in dataset.plans for item in plan.subtasks)


def _record(case_id: str, group: str, index: int, outcome: Outcome, titles: frozenset[str]) -> RunRecord:
    return RunRecord(
        case_id=case_id,
        group=group,
        index=index,
        kind=outcome.kind,
        reply=outcome.reply,
        lines=outcome.lines,
        rounds=outcome.rounds,
        laws=outcome.laws,
        dataset_titles=titles,
    )


def _print_progress(done: int, total: int, case_id: str, kinds: tuple[str, ...]) -> None:
    """Một dòng tiến độ ra stderr. Không in câu trả lời hay dòng log."""

    print(f"[{done}/{total}] {case_id} {' '.join(kinds)}", file=sys.stderr, flush=True)


def _print_report(runs: list[RunRecord]) -> None:
    report = summarize(runs)
    print(f"input_tokens={report.input_tokens} output_tokens={report.output_tokens}")
    for item in report.by_case:
        rate = "null" if item.rate is None else f"{item.rate:.3f}"
        print(
            f"case {item.id} group={item.group} rate={rate} "
            f"run_errors={item.run_errors} cap_stops={item.cap_stops}"
        )
    for item in report.by_rule:
        print(f"rule {item.name} passed={item.passed} considered={item.considered}")
    for item in report.by_group:
        rate = "null" if item.rate is None else f"{item.rate:.3f}"
        print(
            f"group {item.group} rate={rate} "
            f"run_errors={item.run_errors} cap_stops={item.cap_stops}"
        )


def run_suite(
    env: Mapping[str, str],
    client: ModelClient,
    output_dir: Path,
    day: date,
    cases_path: Path,
    datasets_dir: Path,
) -> int:
    """Chạy cả bộ. Thư mục ra và ngày là tham số bắt buộc."""

    key = check_key(env, client)
    if key is None:
        return 2
    try:
        suite = load_suite(cases_path, datasets_dir)
    except LoadError as error:
        print(error, file=sys.stderr)
        return 2
    try:
        batches = asyncio.run(
            run_cases(
                suite.cases,
                client,
                key,
                datasets=suite.datasets,
                on_case_done=_print_progress,
            )
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        return stop_interrupted(env, client)
    runs: list[RunRecord] = []
    for case, batch in zip(suite.cases, batches, strict=True):
        titles = _titles(suite, case.dataset)
        for index, outcome in enumerate(batch, start=1):
            runs.append(_record(case.id, case.group.value, index, outcome, titles))
    write_result(output_dir, day, runs, cases_version=suite.cases_version, api_key=key)
    _print_report(runs)
    return 0


def main() -> None:
    """Đọc môi trường, dựng adapter, lấy ngày, và chạy bộ vào evals/results."""

    from clients.anthropic_model import AnthropicModel

    code = run_suite(
        os.environ,
        AnthropicModel(),
        Path("evals/results"),
        date.today(),
        Path("evals/cases/v1.json"),
        Path("evals/datasets"),
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
