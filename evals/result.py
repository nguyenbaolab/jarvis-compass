"""Ghi một file kết quả mới. Ngày và thư mục ra do người gọi truyền."""

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from evals.log_lines import parse_log_rows
from evals.redact import redact
from evals.score import _new_titles
from evals.summary import ERROR_KINDS, RunRecord, summarize


def _labels(runs: Sequence[RunRecord]) -> tuple[str, str, str]:
    prompts: list[str] = []
    definitions: list[str] = []
    models: list[str] = []
    for run in runs:
        for row in parse_log_rows(run.lines):
            if "model" not in row:
                continue
            prompts.append(str(row["prompt_version"]))
            definitions.append(str(row["definitions_version"]))
            models.append(str(row["model"]))
    if not models:
        return "trong", "trong", "trong"

    def one(values: list[str]) -> str:
        return values[0] if all(value == values[0] for value in values) else "lech"

    return one(prompts), one(definitions), one(models)


def _safe_model(model: str) -> str:
    return "".join(char if char.isalnum() or char in ".-" else "-" for char in model)


def _path(directory: Path, prompt: str, definitions: str, model: str, day: date) -> Path:
    stem = f"p{prompt}-d{definitions}-{_safe_model(model)}-{day.isoformat()}"
    path = directory / f"{stem}.json"
    if not path.exists():
        return path
    number = 2
    while (directory / f"{stem}-{number}.json").exists():
        number += 1
    return directory / f"{stem}-{number}.json"


def _manual_titles(run: RunRecord) -> list[dict[str, str]]:
    if run.kind in ERROR_KINDS:
        return []
    rows = parse_log_rows(run.lines)
    return [{"title": title, "mark": "unmarked"} for title in _new_titles(rows, run.dataset_titles)]


def write_result(
    directory: Path,
    day: date,
    runs: Sequence[RunRecord],
    *,
    cases_version: int,
    api_key: str,
) -> Path:
    """Ghi đúng một file mới. Không gọi date.today()."""

    hidden: list[RunRecord] = []
    for run in runs:
        reply, lines = redact(run.reply, run.lines, api_key)
        hidden.append(
            RunRecord(
                case_id=run.case_id,
                group=run.group,
                index=run.index,
                kind=run.kind,
                reply=reply,
                lines=lines,
                rounds=run.rounds,
                laws=run.laws,
                dataset_titles=run.dataset_titles,
            )
        )
    report = summarize(hidden)
    prompt, definitions, model = _labels(hidden)
    directory.mkdir(parents=True, exist_ok=True)
    path = _path(directory, prompt, definitions, model, day)
    body = {
        "cases_version": cases_version,
        "prompt_version": prompt,
        "definitions_version": definitions,
        "model": model,
        "date": day.isoformat(),
        "input_tokens": report.input_tokens,
        "output_tokens": report.output_tokens,
        "by_case": [
            {
                "id": item.id,
                "group": item.group,
                "rate": item.rate,
                "run_errors": item.run_errors,
                "cap_stops": item.cap_stops,
            }
            for item in report.by_case
        ],
        "by_rule": [
            {"name": item.name, "passed": item.passed, "considered": item.considered}
            for item in report.by_rule
        ],
        "by_group": [
            {
                "group": item.group,
                "rate": item.rate,
                "run_errors": item.run_errors,
                "cap_stops": item.cap_stops,
            }
            for item in report.by_group
        ],
        "runs": [
            {
                "id": run.case_id,
                "index": run.index,
                "kind": run.kind,
                "reply": run.reply,
                "lines": list(run.lines),
                "rounds": run.rounds,
                "laws": run.laws,
                "manual_titles": _manual_titles(run),
            }
            for run in hidden
        ],
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
