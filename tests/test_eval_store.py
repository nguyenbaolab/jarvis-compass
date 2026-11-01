"""Dựng MemoryPlanStore từ bộ dữ liệu đã đọc."""

import asyncio

from core.plans import SubtaskStatus
from evals.model import Dataset, PlanSeed, SubtaskSeed
from evals.store import build_store


def _dataset() -> Dataset:
    return Dataset(
        name="kho",
        plans=(
            PlanSeed(
                goal="Đọc sách",
                subtasks=(
                    SubtaskSeed(title="Chương 1", status="done", note="xong"),
                    SubtaskSeed(title="Chương 2", status="skipped", note=None),
                ),
            ),
            PlanSeed(goal="Chạy bộ", subtasks=()),
        ),
    )


def test_builds_store_in_file_order() -> None:
    """Thứ tự kế hoạch và việc con theo file. Trạng thái và ghi chú được giữ."""

    store = asyncio.run(build_store(_dataset()))
    plans = asyncio.run(store.list_newest_first())
    oldest_first = tuple(reversed(plans))
    assert [plan.goal for plan in oldest_first] == ["Đọc sách", "Chạy bộ"]
    first = oldest_first[0].subtasks
    assert [item.title for item in first] == ["Chương 1", "Chương 2"]
    assert first[0].status == SubtaskStatus.DONE
    assert first[0].note == "xong"
    assert first[1].status == SubtaskStatus.SKIPPED
    assert first[1].note is None


def test_two_builds_do_not_share_state() -> None:
    """Hai lần dựng cùng một bộ cho hai kho độc lập."""

    first = asyncio.run(build_store(_dataset()))
    second = asyncio.run(build_store(_dataset()))
    asyncio.run(first.add("thêm", ()))
    assert len(asyncio.run(second.list_newest_first())) == 2


def test_empty_dataset_is_empty_store() -> None:
    """Không có bộ dữ liệu thì kho không có kế hoạch."""

    store = asyncio.run(build_store(None))
    assert asyncio.run(store.list_newest_first()) == ()
