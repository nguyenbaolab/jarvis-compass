"""Ba câu, mười một mẫu, và hàm ghép nằm một chỗ."""

from pathlib import Path

from tools import saved_reply
from tools.saved_reply import (
    REJECTED_SENTENCE,
    UNAVAILABLE_SENTENCE,
    UNCERTAIN_SENTENCE,
    compose,
    saved_add,
    saved_clear_effort,
    saved_clear_note,
    saved_clear_priority,
    saved_create,
    saved_note,
    saved_reschedule,
    saved_set_effort,
    saved_set_priority,
    saved_status,
)

_SENTENCES = (
    "Chưa chắc thay đổi đã được lưu.",
    "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.",
    "Không thực hiện được yêu cầu này.",
)
_SAMPLES = (
    "Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana.",
    "Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana, Mua vở.",
    "Đã lưu kế hoạch Học tiếng Nhật.",
    "Đã lưu việc Mua vở vào kế hoạch Học tiếng Nhật.",
    "Đã lưu việc Học hiragana trong kế hoạch Học tiếng Nhật là chưa làm.",
    "Đã lưu việc Học hiragana trong kế hoạch Học tiếng Nhật là xong.",
    "Đã lưu việc Học hiragana trong kế hoạch Học tiếng Nhật là bỏ qua.",
    "Đã lưu ghi chú Đợi giáo trình cho việc Học hiragana trong kế hoạch Học tiếng Nhật.",
    "Đã bỏ ghi chú của việc Học hiragana trong kế hoạch Học tiếng Nhật.",
    "Đã lưu ưu tiên cao cho kế hoạch Học tiếng Nhật.",
    "Đã bỏ ưu tiên của kế hoạch Học tiếng Nhật.",
    "Đã lưu sức S cho việc Học hiragana trong kế hoạch Học tiếng Nhật.",
    "Đã bỏ sức của việc Học hiragana trong kế hoạch Học tiếng Nhật.",
    "Đã lưu ngày của việc Học hiragana trong kế hoạch Học tiếng Nhật.",
)


def test_sentences_and_templates_match_spec() -> None:
    assert UNCERTAIN_SENTENCE == _SENTENCES[0]
    assert REJECTED_SENTENCE == _SENTENCES[1]
    assert UNAVAILABLE_SENTENCE == _SENTENCES[2]
    assert saved_create("Học tiếng Nhật", ("Học hiragana",)) == _SAMPLES[0]
    assert saved_create("Học tiếng Nhật", ("Học hiragana", "Mua vở")) == _SAMPLES[1]
    assert saved_create("Học tiếng Nhật", ()) == _SAMPLES[2]
    assert saved_add("Mua vở", "Học tiếng Nhật") == _SAMPLES[3]
    assert saved_status("Học hiragana", "Học tiếng Nhật", "chưa làm") == _SAMPLES[4]
    assert saved_status("Học hiragana", "Học tiếng Nhật", "xong") == _SAMPLES[5]
    assert saved_status("Học hiragana", "Học tiếng Nhật", "bỏ qua") == _SAMPLES[6]
    assert saved_note("Đợi giáo trình", "Học hiragana", "Học tiếng Nhật") == _SAMPLES[7]
    assert saved_clear_note("Học hiragana", "Học tiếng Nhật") == _SAMPLES[8]


def test_compose_orders_saved_then_uncertain_then_rejected() -> None:
    saved = saved_reply.Saved("Đã lưu kế hoạch Học tiếng Nhật.")
    uncertain = saved_reply.Abandoned()
    rejected = saved_reply.Rejected()
    both = compose((saved_reply.Saved("Dòng một"), saved_reply.Saved("Dòng hai")))
    assert both == "1. Dòng một\n2. Dòng hai"
    assert compose((saved, uncertain)) == f"1. {saved.text}\n{UNCERTAIN_SENTENCE}"
    assert compose((saved, rejected)) == f"1. {saved.text}\n{REJECTED_SENTENCE}"
    assert compose((uncertain,)) == UNCERTAIN_SENTENCE
    assert compose((rejected,)) == REJECTED_SENTENCE
    assert compose((saved, uncertain, rejected)) == (
        f"1. {saved.text}\n{UNCERTAIN_SENTENCE}\n{REJECTED_SENTENCE}"
    )
    assert "\n\n" not in compose((saved, uncertain, rejected))


def test_saved_set_priority_line() -> None:
    assert saved_set_priority("cao", "Học tiếng Nhật") == _SAMPLES[9]


def test_saved_clear_priority_line() -> None:
    assert saved_clear_priority("Học tiếng Nhật") == _SAMPLES[10]


def test_saved_set_effort_line() -> None:
    assert saved_set_effort("S", "Học hiragana", "Học tiếng Nhật") == _SAMPLES[11]


def test_saved_clear_effort_line() -> None:
    assert saved_clear_effort("Học hiragana", "Học tiếng Nhật") == _SAMPLES[12]


def test_saved_reschedule_line() -> None:
    assert saved_reschedule(("Học hiragana",), "Học tiếng Nhật") == _SAMPLES[13]
    assert saved_reschedule(("Học hiragana", "Mua vở"), "Học tiếng Nhật") == (
        "Đã lưu ngày của việc Học hiragana, Mua vở trong kế hoạch Học tiếng Nhật."
    )


def test_fixed_strings_live_only_in_saved_reply() -> None:
    root = Path(__file__).parents[1] / "src"
    needles = _SENTENCES + _SAMPLES
    hits = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            hits.append(path.relative_to(root).as_posix())
    assert hits == ["tools/saved_reply.py"]
