"""Mô phỏng compass trên kho giả. Không mạng, không Supabase, không mô hình."""

import asyncio
import difflib
from collections import Counter
from datetime import date
from pathlib import Path

from core.plans import Effort, Subtask, SubtaskStatus
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.simulation.fortnight import build_fortnight_markdown
from tests.simulation.harness import BotOwner, CountingStore, assert_no_ids, at_helsinki
from tests.simulation.random_days import ALL_SEEDS, empty_counts, run_seed

_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN = _ROOT / "docs" / "simulation" / "fortnight.md"
_RERUN = (
    "PYTHONPATH=src uv run python -m tests.simulation.runner "
    "--write docs/simulation/fortnight.md"
)


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def test_fortnight_transcript_matches_golden() -> None:
    text = asyncio.run(build_fortnight_markdown())
    assert_no_ids(text)
    if not _GOLDEN.is_file():
        raise AssertionError(f"Thiếu file vàng. Chạy lại: {_RERUN}")
    raw = _GOLDEN.read_bytes()
    if b"\r\n" not in raw or b"\n" in raw.replace(b"\r\n", b""):
        raise AssertionError(f"File vàng không phải CRLF. Chạy lại: {_RERUN}")
    expected = _normalize(_GOLDEN.read_text(encoding="utf-8"))
    if text != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile="docs/simulation/fortnight.md",
                tofile="fortnight",
            )
        )
        raise AssertionError(f"Bản ghi lệch file vàng. Chạy lại: {_RERUN}\n{diff[:4000]}")


def test_random_seed_11() -> None:
    asyncio.run(run_seed(11))


def test_random_seed_29() -> None:
    asyncio.run(run_seed(29))


def test_random_seed_47() -> None:
    asyncio.run(run_seed(47))


def test_random_seed_83_replace_fails_midway() -> None:
    asyncio.run(run_seed(83))


def test_random_seed_97_second_replace_of_confirm() -> None:
    asyncio.run(run_seed(97))


def test_random_seed_131_second_replace_of_confirm() -> None:
    asyncio.run(run_seed(131))


def test_partial_sentence_counts_the_request_separately() -> None:
    asyncio.run(_partial_sentence_counts_the_request_separately())


_MINIMUMS = {
    "warnings_load": 10,
    "confirmed_ok": 5,
    "declined": 3,
    "warnings_clash": 1,
    "partial_sentences": 2,
    "moves_applied": 5,
}


def test_random_days_cover_the_interesting_paths() -> None:
    totals = empty_counts()
    per_seed: dict[int, Counter] = {}
    for seed in ALL_SEEDS:
        counts = asyncio.run(run_seed(seed))
        per_seed[seed] = counts
        totals.update(counts)
    short = [
        f"{key}={totals[key]} < {minimum}"
        for key, minimum in _MINIMUMS.items()
        if totals[key] < minimum
    ]
    if short:
        detail = "; ".join(f"{seed}={dict(per_seed[seed])}" for seed in ALL_SEEDS)
        raise AssertionError("Độ phủ chưa đủ, không hạ ngưỡng. " + ", ".join(short) + "\n" + detail)


async def _partial_sentence_counts_the_request_separately() -> None:
    inner = MemoryPlanStore()
    store = CountingStore(inner)
    plan = await inner.add(
        "Một",
        (
            Subtask(
                id="xin",
                title="Việc xin",
                status=SubtaskStatus.PENDING,
                note=None,
                scheduled_on=date(2026, 11, 16),
                effort=Effort.S,
            ),
            Subtask(
                id="doi",
                title="Việc dời",
                status=SubtaskStatus.PENDING,
                note=None,
                scheduled_on=date(2026, 11, 17),
                effort=Effort.S,
            ),
        ),
    )
    store.prepare_call(fail_second_replace=True)
    result = await BotOwner(store).tool(
        "reschedule_subtasks",
        {
            "plan_id": plan.id,
            "changes": [{"subtask_id": "xin", "scheduled_on": "2026-11-20"}],
            "confirm": True,
            "load_moves": [
                {"plan_id": plan.id, "subtask_id": "doi", "scheduled_on": "2026-11-21"},
            ],
        },
        at_helsinki(date(2026, 11, 16), 9),
    )
    assert result.success is False
    assert result.output == "Đã ghi lần đang xin. Đã dời: . Chưa dời: Việc dời."
    saved = await inner.get(plan.id)
    assert saved is not None
    by_id = {item.id: item.scheduled_on for item in saved.subtasks}
    assert by_id["xin"] == date(2026, 11, 20)
    assert by_id["doi"] == date(2026, 11, 17)
