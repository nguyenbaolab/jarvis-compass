"""Luật chữ của bản tin sáng. Không đồng hồ, không kênh, không mô hình."""

from core.morning import is_next_command, render_digest
from core.plans import Plan, Subtask, SubtaskStatus

_EMPTY = "Không còn việc chưa làm."


def _subtask(title: str, status: SubtaskStatus, note: str | None = None) -> Subtask:
    return Subtask(id=title, title=title, status=status, note=note)


def _plan(order: int, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
    return Plan(id=f"plan-{order}", goal=goal, subtasks=subtasks, created_order=order, version=1)


def test_oldest_created_order_comes_first() -> None:
    newer = _plan(2, "Mới", (_subtask("sau", SubtaskStatus.PENDING),))
    older = _plan(1, "Cũ", (_subtask("trước", SubtaskStatus.PENDING),))
    assert render_digest((newer, older)) == "Cũ\ntrước\n\nMới\nsau"


def test_plan_without_pending_has_no_segment() -> None:
    done = _plan(1, "Xong", (_subtask("a", SubtaskStatus.DONE, "ghi"),))
    skipped = _plan(2, "Bỏ", (_subtask("b", SubtaskStatus.SKIPPED),))
    live = _plan(3, "Còn", (_subtask("c", SubtaskStatus.PENDING),))
    assert render_digest((done, skipped, live)) == "Còn\nc"


def test_zero_segments_is_the_fixed_sentence() -> None:
    done = _plan(1, "Xong", (_subtask("a", SubtaskStatus.DONE),))
    assert render_digest(()) == _EMPTY
    assert render_digest((done,)) == _EMPTY


def test_next_command_matches_case_and_surrounding_space() -> None:
    assert is_next_command("/Next") is True
    assert is_next_command(" /next ") is True


def test_next_command_rejects_bot_suffix() -> None:
    assert is_next_command("/next@bot") is False


def test_same_plans_return_the_same_string_without_a_clock() -> None:
    plans = (_plan(1, "Học", (_subtask("đọc", SubtaskStatus.PENDING),)),)
    first = render_digest(plans)
    second = render_digest(plans)
    assert first == second == "Học\nđọc"
    assert "2026" not in first
    assert "Helsinki" not in first
    assert "thứ" not in first


def test_segment_is_goal_newline_and_first_pending_title() -> None:
    plan = _plan(
        1,
        "Mục tiêu",
        (
            _subtask("đầu", SubtaskStatus.PENDING),
            _subtask("sau", SubtaskStatus.PENDING),
        ),
    )
    assert render_digest((plan,)) == "Mục tiêu\nđầu"


def test_two_segments_are_separated_by_one_blank_line() -> None:
    first = _plan(1, "Một", (_subtask("a", SubtaskStatus.PENDING),))
    second = _plan(2, "Hai", (_subtask("b", SubtaskStatus.PENDING),))
    assert render_digest((second, first)) == "Một\na\n\nHai\nb"


def test_done_and_skipped_subtasks_are_skipped() -> None:
    plan = _plan(
        1,
        "Mục",
        (
            _subtask("xong", SubtaskStatus.DONE),
            _subtask("bỏ", SubtaskStatus.SKIPPED),
            _subtask("còn", SubtaskStatus.PENDING),
        ),
    )
    assert render_digest((plan,)) == "Mục\ncòn"


def test_notes_are_not_in_the_text() -> None:
    plan = _plan(1, "Mục", (_subtask("còn", SubtaskStatus.PENDING, "ghi chú bí mật"),))
    assert render_digest((plan,)) == "Mục\ncòn"


def test_pending_title_keeps_a_stored_date() -> None:
    title = "Nộp bài (thứ Sáu 06/11)"
    plan = _plan(1, "Mục", (_subtask(title, SubtaskStatus.PENDING),))
    assert render_digest((plan,)) == f"Mục\n{title}"


def test_a_later_pending_title_is_left_out() -> None:
    plan = _plan(
        1,
        "Mục",
        (
            _subtask("đầu", SubtaskStatus.PENDING),
            _subtask("sau (thứ Sáu 06/11)", SubtaskStatus.PENDING),
        ),
    )
    text = render_digest((plan,))
    assert text == "Mục\nđầu"
    assert "sau" not in text


def test_markdown_characters_stay_literal() -> None:
    plan = _plan(1, "a*b_c`d", (_subtask("e*f_g`h", SubtaskStatus.PENDING),))
    assert render_digest((plan,)) == "a*b_c`d\ne*f_g`h"


def test_text_has_no_greeting_closing_ids_or_status_names() -> None:
    plan = _plan(9, "Mục", (_subtask("Việc", SubtaskStatus.PENDING),))
    text = render_digest((plan,))
    assert text == "Mục\nViệc"
    for extra in ("Chào", "Xin chào", "pending", "done", "skipped", "plan-9"):
        assert extra not in text
