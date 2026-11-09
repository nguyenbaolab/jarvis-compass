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


def test_trung_han_loads() -> None:
    """Seed trung_han có đủ việc, trạng thái và ngày."""

    from pathlib import Path

    from evals.load import load_suite

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    plan = {item.goal: item for item in suite.datasets["trung_han"].plans}
    physics = [(item.title, item.status, item.scheduled_on) for item in plan["Ôn thi vật lý"].subtasks]
    assert physics == [
        ("Đọc xong tài liệu chương 1", "done", "2026-11-13"),
        ("Làm xong bài tập chương 1", "pending", "2026-11-11"),
        ("Làm xong đề thi thử", "pending", "2026-11-13"),
    ]
    thesis = [(item.title, item.status, item.scheduled_on) for item in plan["Nộp luận văn"].subtasks]
    assert thesis == [("Nộp bản cuối cho giáo viên", "pending", "2026-11-14")]


def test_trung_han_san_loads() -> None:
    """Seed trung_han_san không có việc đã xong."""

    from pathlib import Path

    from evals.load import load_suite

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    plan = {item.goal: item for item in suite.datasets["trung_han_san"].plans}
    physics = [(item.title, item.status, item.scheduled_on) for item in plan["Ôn thi vật lý"].subtasks]
    assert physics == [
        ("Làm xong bài tập chương 1", "pending", "2026-11-11"),
        ("Làm xong đề thi thử", "pending", "2026-11-14"),
    ]


def test_ke_hoach_khong_ngay_loads() -> None:
    """Ba việc chạy đều pending và không ngày."""

    from pathlib import Path

    from evals.load import load_suite

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    items = suite.datasets["ke_hoach_khong_ngay"].plans[0].subtasks
    assert [(item.title, item.status, item.scheduled_on) for item in items] == [
        ("Chạy 6km không nghỉ", "pending", None),
        ("Chạy 8km không nghỉ", "pending", None),
        ("Chạy 10km không nghỉ", "pending", None),
    ]


def test_bang_chu_cai_tach_loads() -> None:
    """Hai việc tách Hiragana và Katakana."""

    from pathlib import Path

    from evals.load import load_suite

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    items = suite.datasets["bang_chu_cai_tach"].plans[0].subtasks
    assert [item.title for item in items] == ["Học thuộc bảng Hiragana", "Học thuộc bảng Katakana"]
    assert all(item.status == "pending" for item in items)


def test_bang_chu_cai_gop_loads() -> None:
    """Một việc gộp và một việc Kanji."""

    from pathlib import Path

    from evals.load import load_suite

    root = Path(__file__).parents[1]
    suite = load_suite(root / "evals" / "cases" / "v2.json", root / "evals" / "datasets")
    items = suite.datasets["bang_chu_cai_gop"].plans[0].subtasks
    assert [item.title for item in items] == [
        "Học thuộc bảng Hiragana và Katakana",
        "Học 50 chữ Kanji đầu tiên",
    ]
    assert all(item.status == "pending" and item.scheduled_on is None for item in items)
