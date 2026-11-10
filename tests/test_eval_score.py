"""Luật chấm từ log và kho ghi sẵn. Không gọi run_turn và không mở mạng."""

import asyncio
import json

from core.plans import Subtask, SubtaskStatus, new_subtask, normalize_new_plan, normalize_subtask_note
from evals.score import StoreExpectation, law_results
from tests.fakes.memory_plan_store import MemoryPlanStore

_MODEL_KEYS = (
    "model",
    "prompt_version",
    "definitions_version",
    "stop_reason",
    "input_tokens",
    "output_tokens",
    "duration_ms",
    "error_type",
)
_TOOL_KEYS = (
    "tool",
    "input",
    "ok",
    "error_type",
    "duration_ms",
    "definitions_version",
    "detail",
)


def _model_line() -> str:
    payload = {
        "model": "claude-haiku-5-5",
        "prompt_version": 1,
        "definitions_version": 1,
        "stop_reason": "end_turn",
        "input_tokens": 1,
        "output_tokens": 1,
        "duration_ms": 0,
        "error_type": None,
    }
    return json.dumps({key: payload[key] for key in _MODEL_KEYS}, ensure_ascii=False)


def _tool(name: str, tool_input: object) -> str:
    payload = {
        "tool": name,
        "input": tool_input,
        "ok": True,
        "error_type": None,
        "duration_ms": 0,
        "definitions_version": 1,
        "detail": None,
    }
    return json.dumps({key: payload[key] for key in _TOOL_KEYS}, ensure_ascii=False)


def _score(group: str, reply: str, lines: list[str], **kwargs: object) -> dict[str, str]:
    return asyncio.run(
        law_results(group, reply, lines, **kwargs)  # type: ignore[arg-type]
    )


def test_update_group_rejects_set_note() -> None:
    """Ca cập nhật gọi set_subtask_note thì luật đúng tool trượt."""

    bad = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [_model_line(), _tool("set_subtask_note", {"plan_id": "p", "subtask_id": "s", "note": "n"})],
    )
    assert bad["tool"] == "fail"
    quiet = _score("cập nhật trạng thái việc con", "Xong.", [_model_line()])
    assert quiet["tool"] == "pass"
    good = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [
            _model_line(),
            _tool("get_plans", {}),
            _tool("get_plan_detail", {"plan_id": "p"}),
            _tool("update_subtask", {"plan_id": "p", "subtask_id": "s", "status": "done"}),
        ],
    )
    assert good["tool"] == "pass"


def test_no_tool_group_rejects_any_tool() -> None:
    """Nhóm không gọi tool: đạt khi không tool, trượt khi có một tool."""

    quiet = _score("chỉ kể việc", "Mình nghe.", [_model_line()])
    assert quiet["tool"] == "pass"
    noisy = _score("chỉ kể việc", "Mình nghe.", [_model_line(), _tool("get_plans", {})])
    assert noisy["tool"] == "fail"
    for group in ("chào hỏi", "câu mơ hồ", "câu ngoài phạm vi"):
        assert _score(group, "Mình nghe.", [_model_line()])["tool"] == "pass"
        assert _score(group, "Mình nghe.", [_model_line(), _tool("get_plans", {})])["tool"] == "fail"


def test_list_group_rejects_other_tools() -> None:
    """Hỏi danh sách chỉ đạt khi mọi lần gọi là get_plans và có ít nhất một lần."""

    good = _score("hỏi danh sách", "Có hai kế hoạch.", [_model_line(), _tool("get_plans", {})])
    assert good["tool"] == "pass"
    bad = _score(
        "hỏi danh sách",
        "Có hai kế hoạch.",
        [_model_line(), _tool("get_plans", {}), _tool("get_plan_detail", {"plan_id": "p"})],
    )
    assert bad["tool"] == "fail"


def test_detail_group_requires_get_plan_detail() -> None:
    """Xem chi tiết chỉ đạt khi có get_plan_detail. get_plans trước đó được phép."""

    good = _score(
        "xem chi tiết",
        "Đây là kế hoạch.",
        [_model_line(), _tool("get_plans", {}), _tool("get_plan_detail", {"plan_id": "p"})],
    )
    assert good["tool"] == "pass"
    only_list = _score("xem chi tiết", "Đây là kế hoạch.", [_model_line(), _tool("get_plans", {})])
    assert only_list["tool"] == "fail"
    wrote = _score(
        "xem chi tiết",
        "Đây là kế hoạch.",
        [
            _model_line(),
            _tool("get_plan_detail", {"plan_id": "p"}),
            _tool("update_subtask", {"plan_id": "p", "subtask_id": "s", "status": "done"}),
        ],
    )
    assert wrote["tool"] == "fail"


def test_create_plan_count_fail_on_two() -> None:
    """Nhờ lập kế hoạch cần đúng một create_plan. Nhóm khác cần số lần bằng 0."""

    one = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [_model_line(), _tool("create_plan", {"goal": "Đọc sách"})],
    )
    assert one["tool"] == "pass"
    assert one["create_plan_count"] == "pass"
    two = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [
            _model_line(),
            _tool("create_plan", {"goal": "Đọc sách"}),
            _tool("create_plan", {"goal": "Chạy bộ"}),
        ],
    )
    assert two["tool"] == "fail"
    assert two["create_plan_count"] == "fail"
    extra = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [_model_line(), _tool("create_plan", {"goal": "Đọc sách"})],
    )
    assert extra["create_plan_count"] == "fail"


def test_required_param_missing_goal() -> None:
    """Thiếu trường bắt buộc thì trượt. Không có tool thì đạt."""

    missing = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [_model_line(), _tool("create_plan", {})],
    )
    assert missing["required"] == "fail"
    present = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [_model_line(), _tool("create_plan", {"goal": "Đọc sách"})],
    )
    assert present["required"] == "pass"
    quiet = _score("chỉ kể việc", "Mình nghe.", [_model_line()])
    assert quiet["required"] == "pass"
    not_object = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [_model_line(), _tool("create_plan", "không phải object")],
    )
    assert not_object["required"] == "fail"
    unknown = _score(
        "chỉ kể việc",
        "Mình nghe.",
        [_model_line(), _tool("không_có", {})],
    )
    assert unknown["required"] == "fail"


def test_prefix_fails_on_ordinal_words() -> None:
    """Tiền tố thứ tự trượt. Tiêu đề đã có trong bộ dữ liệu không bị xét."""

    titles = [
        "Ngày 1: nộp báo cáo",
        "ngày 1: nộp báo cáo",
        "Tuần 1: ôn tập",
        "1. học",
        "Bước 1 viết",
        "Giai đoạn 2: ôn",
    ]
    for title in titles:
        bad = _score(
            "nhờ lập kế hoạch",
            "Đã lập.",
            [_model_line(), _tool("create_plan", {"goal": "Học", "subtasks": [title]})],
        )
        assert bad["prefix"] == "fail", title
    good = _score(
        "nhờ lập kế hoạch",
        "Đã lập.",
        [_model_line(), _tool("create_plan", {"goal": "Học", "subtasks": ["Nộp báo cáo thứ Sáu"]})],
    )
    assert good["prefix"] == "pass"
    seeded = _score(
        "thêm việc con",
        "Đã thêm.",
        [_model_line(), _tool("add_subtask", {"plan_id": "p", "title": "Ngày 1: cũ"})],
        dataset_titles=frozenset({"Ngày 1: cũ"}),
    )
    assert seeded["prefix"] == "pass"
    quiet = _score("chỉ kể việc", "Mình nghe.", [_model_line()])
    assert quiet["prefix"] == "pass"


def test_prefix_nfc_composed_and_combining() -> None:
    """Chuỗi dựng sẵn và chuỗi tổ hợp cùng nội dung cho cùng kết quả tiền tố."""

    composed = "Ngày 1: nộp"
    combining = unicodedata_nfd(composed)
    assert composed != combining
    for title in (composed, combining):
        result = _score(
            "nhờ lập kế hoạch",
            "Đã lập.",
            [_model_line(), _tool("create_plan", {"goal": "Học", "subtasks": [title]})],
        )
        assert result["prefix"] == "fail"


def unicodedata_nfd(value: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFD", value)


def test_markdown_allows_numbered_and_dash() -> None:
    """Dòng số và gạch ngang không làm luật Markdown trượt."""

    reply = "1. Chạy 2km\n- Nộp báo cáo"
    assert _score("chỉ kể việc", reply, [_model_line()])["markdown"] == "pass"
    plus = "+ Nộp báo cáo"
    assert _score("chỉ kể việc", plus, [_model_line()])["markdown"] == "pass"


def test_markdown_rejects_star() -> None:
    """Các dấu Markdown bị cấm làm luật trượt."""

    samples = [
        "có ```khối```",
        "có `mã`",
        "có **đậm**",
        "có __đậm__",
        "xem [đây](http://example.invalid)",
        "# Tiêu đề",
        "* một mục",
    ]
    for reply in samples:
        assert _score("chỉ kể việc", reply, [_model_line()])["markdown"] == "fail"


def test_self_name_rejects_phrase() -> None:
    """Đúng cụm tự xưng thì trượt. Không phân biệt hoa thường là không áp vào cụm này."""

    bad = _score("chỉ kể việc", "Mình là trợ lý lập kế hoạch.", [_model_line()])
    assert bad["self_name"] == "fail"
    good = _score("chỉ kể việc", "Mình nghe.", [_model_line()])
    assert good["self_name"] == "pass"
    other_case = _score("chỉ kể việc", "Mình là Trợ Lý Lập Kế Hoạch.", [_model_line()])
    assert other_case["self_name"] == "pass"


async def _filled(goal: str, title: str, status: str, note: str | None) -> MemoryPlanStore:
    store = MemoryPlanStore()
    goal_text, _ = normalize_new_plan(goal, None)
    base = new_subtask(title)
    item = Subtask(
        id=base.id,
        title=base.title,
        status=SubtaskStatus(status),
        note=normalize_subtask_note(note),
    )
    await store.add(goal_text, (item,))
    return store


def test_store_update_requires_new_status() -> None:
    """Luật kho chỉ xét ba nhóm ghi và so với kỳ vọng."""

    matched = asyncio.run(_filled("Đọc sách", "Chương 3", "done", None))
    passed = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [_model_line(), _tool("update_subtask", {"plan_id": "p", "subtask_id": "s", "status": "done"})],
        store=matched,
        expectation=StoreExpectation(
            kind="update_status",
            goal="Đọc sách",
            title="Chương 3",
            status="done",
        ),
    )
    assert passed["store"] == "pass"
    stale = asyncio.run(_filled("Đọc sách", "Chương 3", "pending", None))
    failed = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [_model_line()],
        store=stale,
        expectation=StoreExpectation(
            kind="update_status",
            goal="Đọc sách",
            title="Chương 3",
            status="done",
        ),
    )
    assert failed["tool"] == "pass"
    assert failed["store"] == "fail"
    added = asyncio.run(_filled("Đọc sách", "Bài mới", "pending", None))
    added_pass = _score(
        "thêm việc con",
        "Đã thêm.",
        [_model_line(), _tool("add_subtask", {"plan_id": "p", "title": "Bài mới"})],
        store=added,
        expectation=StoreExpectation(kind="add_subtask", goal="Đọc sách", title="Bài mới"),
    )
    assert added_pass["store"] == "pass"
    noted = asyncio.run(_filled("Đọc sách", "Chương 3", "pending", "đã nộp"))
    note_pass = _score(
        "ghi chú",
        "Đã ghi.",
        [_model_line(), _tool("set_subtask_note", {"plan_id": "p", "subtask_id": "s", "note": "đã nộp"})],
        store=noted,
        expectation=StoreExpectation(kind="set_note", goal="Đọc sách", title="Chương 3", note="đã nộp"),
    )
    assert note_pass["store"] == "pass"
    cleared = asyncio.run(_filled("Đọc sách", "Chương 3", "pending", None))
    clear_pass = _score(
        "ghi chú",
        "Đã xóa.",
        [_model_line(), _tool("set_subtask_note", {"plan_id": "p", "subtask_id": "s", "note": ""})],
        store=cleared,
        expectation=StoreExpectation(kind="set_note", goal="Đọc sách", title="Chương 3", note="   "),
    )
    assert clear_pass["store"] == "pass"
    still = asyncio.run(_filled("Đọc sách", "Chương 3", "pending", "còn"))
    clear_fail = _score(
        "ghi chú",
        "Đã xóa.",
        [_model_line()],
        store=still,
        expectation=StoreExpectation(kind="set_note", goal="Đọc sách", title="Chương 3", note=""),
    )
    assert clear_fail["store"] == "fail"
    narrate = _score("chỉ kể việc", "Mình nghe.", [_model_line()])
    assert narrate["store"] == "not_applicable"


def _item(
    title: str,
    status: str = "pending",
    day: str | None = None,
    effort: str | None = None,
) -> tuple[object, ...]:
    return (title, status, None, day, effort)


def _image(*plans: tuple[object, ...]) -> tuple[object, ...]:
    return plans


def _one(goal: str, *items: tuple[object, ...], priority: str | None = None) -> tuple[object, ...]:
    return (goal, priority, items)


def _v2(kind: str, lines: list[str], **kwargs: object) -> dict[str, str]:
    from evals.model import Expectation

    detail = kwargs.pop("detail", None)
    if detail is None:
        detail = Expectation(kind=kind)
    return _score(
        "nhóm",
        "Mình nghe.",
        lines,
        cases_version=2,
        detail=detail,
        **kwargs,
    )


def test_scorer_v2_scores_v1_case_like_v1() -> None:
    """Nhánh v1 không đọc ngày đã lưu. Việc có ngày vẫn đạt luật kho của bản 1."""

    from datetime import date

    async def filled() -> MemoryPlanStore:
        store = MemoryPlanStore()
        goal, _ = normalize_new_plan("Đọc sách", None)
        base = new_subtask("Chương 1")
        item = Subtask(
            id=base.id,
            title=base.title,
            status=SubtaskStatus.DONE,
            note=normalize_subtask_note(None),
            scheduled_on=date(2026, 11, 6),
        )
        await store.add(goal, (item,))
        return store

    store = asyncio.run(filled())
    laws = _score(
        "cập nhật trạng thái việc con",
        "Xong.",
        [_model_line(), _tool("update_subtask", {"plan_id": "p", "subtask_id": "s", "status": "done"})],
        store=store,
        expectation=StoreExpectation(kind="update_status", goal="Đọc sách", title="Chương 1", status="done"),
        cases_version=1,
    )
    assert laws["store"] == "pass"
    assert laws["tool"] == "pass"


def test_two_turn_case_reads_store_between_turns() -> None:
    """Ảnh sau lượt 1 bằng ảnh lúc mở. Sau lượt 2 ngày và số dòng lịch sử khớp kỳ vọng."""

    from evals.model import Expectation

    opening = _image(
        _one(
            "Ôn thi vật lý",
            _item("Đọc xong tài liệu chương 1", "done", "2026-11-13"),
            _item("Làm xong bài tập chương 1", "pending", "2026-11-11"),
            _item("Làm xong đề thi thử", "pending", "2026-11-13"),
        ),
        _one("Nộp luận văn", _item("Nộp bản cuối cho giáo viên", "pending", "2026-11-14")),
    )
    closing = _image(
        _one(
            "Ôn thi vật lý",
            _item("Đọc xong tài liệu chương 1", "done", "2026-11-13"),
            _item("Làm xong bài tập chương 1", "pending", "2026-11-11"),
            _item("Làm xong đề thi thử", "pending", "2026-11-14"),
        ),
        _one("Nộp luận văn", _item("Nộp bản cuối cho giáo viên", "pending", "2026-11-14")),
    )
    detail = Expectation(
        kind="clash_two_turn",
        goal="Ôn thi vật lý",
        other_goal="Nộp luận văn",
        dates=(
            ("Đọc xong tài liệu chương 1", "2026-11-13"),
            ("Làm xong bài tập chương 1", "2026-11-11"),
            ("Làm xong đề thi thử", "2026-11-14"),
        ),
        history_moves=1,
    )
    first = [_model_line(), _tool("reschedule_subtasks", {"confirm": False})]
    second = [_model_line(), _tool("reschedule_subtasks", {"confirm": True})]
    laws = _v2(
        "clash_two_turn",
        second,
        detail=detail,
        opening=opening,
        after_first=opening,
        closing=closing,
        earlier_lines=first,
        history_count=1,
    )
    assert laws["store"] == "pass"
    assert laws["tool"] == "pass"


def test_prefix_law_reads_title_on_object() -> None:
    """subtasks là object thì luật prefix đọc khóa title."""

    laws = _score(
        "nhờ lập kế hoạch",
        "Xong.",
        [_model_line(), _tool("create_plan", {"goal": "Học", "subtasks": [{"title": "Ngày 1: Hiragana"}]})],
    )
    assert laws["prefix"] == "fail"


def test_prefix_law_still_reads_plain_string() -> None:
    """Cùng tiêu đề là chuỗi thì luật prefix vẫn trượt."""

    laws = _score(
        "nhờ lập kế hoạch",
        "Xong.",
        [_model_line(), _tool("create_plan", {"goal": "Học", "subtasks": ["Ngày 1: Hiragana"]})],
    )
    assert laws["prefix"] == "fail"


def test_create_with_deadline_tool_passes() -> None:
    laws = _v2("create_with_deadline", [_model_line(), _tool("create_plan", {"goal": "Ôn"})])
    assert laws["tool"] == "pass"
    assert laws["create_plan_count"] == "pass"


def test_create_with_deadline_tool_fails() -> None:
    laws = _v2("create_with_deadline", [_model_line(), _tool("get_plans", {})])
    assert laws["tool"] == "fail"


def test_create_with_deadline_store_passes() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc", "pending", "2026-11-15")))
    laws = _v2(
        "create_with_deadline",
        [_model_line()],
        detail=Expectation(kind="create_with_deadline", deadline="2026-11-15"),
        closing=closing,
    )
    assert laws["store"] == "pass"


def test_create_with_deadline_store_fails() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc", "pending", "2026-11-14")))
    laws = _v2(
        "create_with_deadline",
        [_model_line()],
        detail=Expectation(kind="create_with_deadline", deadline="2026-11-15"),
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_ask_back_relative_tool_passes() -> None:
    laws = _v2("ask_back_no_write", [_model_line(), _tool("get_plans", {})])
    assert laws["tool"] == "pass"


def test_ask_back_relative_tool_fails() -> None:
    laws = _v2("ask_back_no_write", [_model_line(), _tool("create_plan", {"goal": "Ôn"})])
    assert laws["tool"] == "fail"


def test_ask_back_relative_store_passes() -> None:
    image = _image(_one("Ôn", _item("Đọc")))
    laws = _v2("ask_back_no_write", [_model_line()], opening=image, closing=image, history_count=0)
    assert laws["store"] == "pass"


def test_ask_back_no_write_fails_when_store_changes() -> None:
    """Bỏ so ảnh kho thì ca này không còn trượt."""

    opening = _image(_one("Ôn", _item("Đọc")))
    closing = _image(_one("Ôn", _item("Đọc", "done")))
    laws = _v2("ask_back_no_write", [_model_line()], opening=opening, closing=closing, history_count=0)
    assert laws["store"] == "fail"


def test_ask_back_ambiguous_tool_passes() -> None:
    laws = _v2("ask_back_no_write", [_model_line()])
    assert laws["tool"] == "pass"


def test_ask_back_ambiguous_tool_fails() -> None:
    laws = _v2("ask_back_no_write", [_model_line(), _tool("reschedule_subtasks", {})])
    assert laws["tool"] == "fail"


def test_ask_back_ambiguous_store_passes() -> None:
    image = _image()
    laws = _v2("ask_back_no_write", [_model_line()], opening=image, closing=image, history_count=0)
    assert laws["store"] == "pass"


def test_ask_back_ambiguous_store_fails() -> None:
    laws = _v2(
        "ask_back_no_write",
        [_model_line()],
        opening=_image(),
        closing=_image(_one("Ôn", _item("Đọc"))),
        history_count=0,
    )
    assert laws["store"] == "fail"


def test_set_deadline_existing_tool_passes() -> None:
    laws = _v2("set_deadline_existing", [_model_line(), _tool("reschedule_subtasks", {"confirm": True})])
    assert laws["tool"] == "pass"


def test_set_deadline_existing_tool_fails() -> None:
    laws = _v2("set_deadline_existing", [_model_line(), _tool("get_plans", {})])
    assert laws["tool"] == "fail"


def test_set_deadline_existing_store_passes() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy", _item("6km"), _item("8km"), _item("10km")))
    closing = _image(_one("Chạy", _item("6km"), _item("8km"), _item("10km", "pending", "2026-11-20")))
    laws = _v2(
        "set_deadline_existing",
        [_model_line()],
        detail=Expectation(kind="set_deadline_existing", goal="Chạy", deadline="2026-11-20"),
        opening=opening,
        closing=closing,
    )
    assert laws["store"] == "pass"


def test_set_deadline_existing_store_fails() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy", _item("6km"), _item("10km")))
    closing = _image(_one("Chạy", _item("6km", "pending", "2026-11-20"), _item("10km", "pending", "2026-11-20")))
    laws = _v2(
        "set_deadline_existing",
        [_model_line()],
        detail=Expectation(kind="set_deadline_existing", goal="Chạy", deadline="2026-11-20"),
        opening=opening,
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_clash_two_turn_tool_passes() -> None:
    first = [_model_line(), _tool("reschedule_subtasks", {"confirm": False})]
    second = [_model_line(), _tool("reschedule_subtasks", {"confirm": True})]
    laws = _v2("clash_two_turn", second, earlier_lines=first)
    assert laws["tool"] == "pass"


def test_clash_two_turn_tool_fails() -> None:
    first = [_model_line(), _tool("reschedule_subtasks", {"confirm": True})]
    second = [_model_line(), _tool("reschedule_subtasks", {"confirm": True})]
    laws = _v2("clash_two_turn", second, earlier_lines=first)
    assert laws["tool"] == "fail"


def test_clash_two_turn_store_passes() -> None:
    from evals.model import Expectation

    opening = _image(_one("Ôn", _item("Việc", "pending", "2026-11-13")), _one("Nộp", _item("Nộp", "pending", "2026-11-14")))
    closing = _image(_one("Ôn", _item("Việc", "pending", "2026-11-14")), _one("Nộp", _item("Nộp", "pending", "2026-11-14")))
    detail = Expectation(
        kind="clash_two_turn",
        goal="Ôn",
        other_goal="Nộp",
        dates=(("Việc", "2026-11-14"),),
        history_moves=1,
    )
    laws = _v2(
        "clash_two_turn",
        [_model_line()],
        detail=detail,
        opening=opening,
        after_first=opening,
        closing=closing,
        history_count=1,
    )
    assert laws["store"] == "pass"


def test_clash_two_turn_store_fails() -> None:
    from evals.model import Expectation

    opening = _image(_one("Ôn", _item("Việc", "pending", "2026-11-13")))
    changed = _image(_one("Ôn", _item("Việc", "pending", "2026-11-14")))
    detail = Expectation(
        kind="clash_two_turn",
        goal="Ôn",
        other_goal="Khác",
        dates=(("Việc", "2026-11-14"),),
        history_moves=1,
    )
    laws = _v2(
        "clash_two_turn",
        [_model_line()],
        detail=detail,
        opening=opening,
        after_first=changed,
        closing=changed,
        history_count=1,
    )
    assert laws["store"] == "fail"


def test_reschedule_no_confirm_tool_passes() -> None:
    laws = _v2("reschedule_no_confirm", [_model_line(), _tool("reschedule_subtasks", {"confirm": False})])
    assert laws["tool"] == "pass"


def test_reschedule_no_confirm_tool_fails() -> None:
    laws = _v2("reschedule_no_confirm", [_model_line(), _tool("reschedule_subtasks", {"confirm": True})])
    assert laws["tool"] == "fail"


def test_reschedule_no_confirm_store_passes() -> None:
    from evals.model import Expectation

    opening = _image(_one("Ôn", _item("Bài", "pending", "2026-11-11")), _one("Nộp", _item("Nộp", "pending", "2026-11-14")))
    closing = _image(_one("Ôn", _item("Bài", "pending", "2026-11-12")), _one("Nộp", _item("Nộp", "pending", "2026-11-14")))
    detail = Expectation(kind="reschedule_no_confirm", goal="Ôn", dates=(("Bài", "2026-11-12"),), history_moves=1)
    laws = _v2(
        "reschedule_no_confirm",
        [_model_line()],
        detail=detail,
        opening=opening,
        closing=closing,
        history_count=1,
    )
    assert laws["store"] == "pass"


def test_reschedule_no_confirm_store_fails() -> None:
    from evals.model import Expectation

    opening = _image(_one("Ôn", _item("Bài", "pending", "2026-11-11")))
    closing = _image(_one("Ôn", _item("Bài", "pending", "2026-11-12")))
    detail = Expectation(kind="reschedule_no_confirm", goal="Ôn", dates=(("Bài", "2026-11-12"),), history_moves=1)
    laws = _v2(
        "reschedule_no_confirm",
        [_model_line()],
        detail=detail,
        opening=opening,
        closing=closing,
        history_count=0,
    )
    assert laws["store"] == "fail"


def test_long_message_goal_tool_passes() -> None:
    laws = _v2("long_message_goal", [_model_line(), _tool("create_plan", {"goal": "Ôn"})])
    assert laws["tool"] == "pass"


def test_long_message_goal_tool_fails() -> None:
    laws = _v2("long_message_goal", [_model_line(), _tool("create_plan", {}), _tool("get_plans", {})])
    assert laws["tool"] == "fail"


def test_long_message_goal_store_passes() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Đọc tài liệu")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "pass"


def test_long_message_goal_store_fails() -> None:
    closing = _image(_one("Ôn trước 20/11", _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_goal_has_spaced_hours() -> None:
    closing = _image(_one("Học Azure 8 tiếng mỗi ngày", _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_goal_has_hour_unit() -> None:
    closing = _image(_one("Ôn AZ-900 2 giờ", _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_goal_has_h_suffix() -> None:
    closing = _image(_one("Ôn AZ-900 8h", _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_goal_is_80_characters() -> None:
    goal = "A" * 80
    assert len(goal) == 80
    closing = _image(_one(goal, _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_passes_when_goal_is_79_characters() -> None:
    goal = "A" * 79
    assert len(goal) == 79
    closing = _image(_one(goal, _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "pass"


def test_long_message_goal_store_fails_when_goal_has_newline() -> None:
    closing = _image(_one("Ôn Azure\nđọc tài liệu", _item("Đọc")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_title_has_lowercase_weekday() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Nộp bài vào thứ sáu")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_passes_when_title_has_ordinal_thu_hai() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Học module thứ hai")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "pass"


def test_long_message_goal_store_passes_when_title_has_ordinal_thu_ba() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Làm đề thi thử thứ ba")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "pass"


def test_long_message_goal_store_fails_when_title_has_capitalized_weekday() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Nộp bài thứ Sáu")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_title_has_lowercase_chu_nhat() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Nộp bài chủ nhật")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_passes_when_title_has_no_date() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Học 3 chương")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "pass"


def test_verbatim_titles_tool_passes() -> None:
    laws = _v2("verbatim_titles", [_model_line(), _tool("create_plan", {"goal": "Học"})])
    assert laws["tool"] == "pass"


def test_verbatim_titles_tool_fails() -> None:
    laws = _v2("verbatim_titles", [_model_line()])
    assert laws["tool"] == "fail"


def test_verbatim_titles_store_passes() -> None:
    from evals.model import Expectation

    closing = _image(_one("Học", _item("Học thuộc bảng Hiragana"), _item("Học thuộc bảng Katakana")))
    detail = Expectation(kind="verbatim_titles", titles=("Học thuộc bảng Hiragana", "Học thuộc bảng Katakana"))
    laws = _v2("verbatim_titles", [_model_line()], detail=detail, closing=closing)
    assert laws["store"] == "pass"


def test_verbatim_titles_store_fails() -> None:
    from evals.model import Expectation

    closing = _image(_one("Học", _item("Hiragana")))
    detail = Expectation(kind="verbatim_titles", titles=("Học thuộc bảng Hiragana",))
    laws = _v2("verbatim_titles", [_model_line()], detail=detail, closing=closing)
    assert laws["store"] == "fail"


def test_create_with_deadline_store_fails_when_priority_is_set() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc", "pending", "2026-11-15"), priority="high"))
    laws = _v2(
        "create_with_deadline",
        [_model_line()],
        detail=Expectation(kind="create_with_deadline", deadline="2026-11-15"),
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_create_with_deadline_store_fails_when_effort_is_set() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc", "pending", "2026-11-15", "M")))
    laws = _v2(
        "create_with_deadline",
        [_model_line()],
        detail=Expectation(kind="create_with_deadline", deadline="2026-11-15"),
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_priority_is_set() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Đọc tài liệu"), priority="high"))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_long_message_goal_store_fails_when_effort_is_set() -> None:
    closing = _image(_one("Ôn AZ-900", _item("Đọc tài liệu", effort="S")))
    laws = _v2("long_message_goal", [_model_line()], closing=closing)
    assert laws["store"] == "fail"


def test_verbatim_titles_store_fails_when_priority_is_set() -> None:
    from evals.model import Expectation

    closing = _image(_one("Học", _item("Học thuộc bảng Hiragana"), priority="low"))
    detail = Expectation(kind="verbatim_titles", titles=("Học thuộc bảng Hiragana",))
    laws = _v2("verbatim_titles", [_model_line()], detail=detail, closing=closing)
    assert laws["store"] == "fail"


def test_verbatim_titles_store_fails_when_effort_is_set() -> None:
    from evals.model import Expectation

    closing = _image(_one("Học", _item("Học thuộc bảng Hiragana", effort="L")))
    detail = Expectation(kind="verbatim_titles", titles=("Học thuộc bảng Hiragana",))
    laws = _v2("verbatim_titles", [_model_line()], detail=detail, closing=closing)
    assert laws["store"] == "fail"


def test_create_with_priority_tool_passes() -> None:
    laws = _v2("create_with_priority", [_model_line(), _tool("create_plan", {"goal": "Ôn"})])
    assert laws["tool"] == "pass"
    assert laws["create_plan_count"] == "pass"


def test_create_with_priority_tool_fails() -> None:
    laws = _v2("create_with_priority", [_model_line(), _tool("get_plans", {})])
    assert laws["tool"] == "fail"


def test_create_with_priority_store_passes() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc"), priority="high"))
    laws = _v2(
        "create_with_priority",
        [_model_line()],
        detail=Expectation(kind="create_with_priority", priority="high"),
        closing=closing,
    )
    assert laws["store"] == "pass"


def test_create_with_priority_store_fails() -> None:
    from evals.model import Expectation

    closing = _image(_one("Ôn", _item("Đọc", effort="S"), priority="high"))
    laws = _v2(
        "create_with_priority",
        [_model_line()],
        detail=Expectation(kind="create_with_priority", priority="high"),
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_set_priority_existing_tool_passes() -> None:
    laws = _v2(
        "set_priority_existing",
        [_model_line(), _tool("get_plans", {}), _tool("set_plan_priority", {"priority": "low"})],
    )
    assert laws["tool"] == "pass"


def test_set_priority_existing_tool_fails() -> None:
    laws = _v2("set_priority_existing", [_model_line(), _tool("get_plans", {})])
    assert laws["tool"] == "fail"


def test_set_priority_existing_store_passes() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy được 10km", _item("Chạy 10km không nghỉ")), _one("Khác", _item("Việc")))
    closing = _image(
        _one("Chạy được 10km", _item("Chạy 10km không nghỉ"), priority="low"),
        _one("Khác", _item("Việc")),
    )
    detail = Expectation(kind="set_priority_existing", goal="Chạy được 10km", priority="low")
    laws = _v2("set_priority_existing", [_model_line()], detail=detail, opening=opening, closing=closing)
    assert laws["store"] == "pass"


def test_set_priority_existing_store_fails() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy được 10km", _item("Chạy 10km không nghỉ")))
    closing = _image(_one("Chạy được 10km", _item("Chạy 10km không nghỉ", "pending", "2026-11-12"), priority="low"))
    detail = Expectation(kind="set_priority_existing", goal="Chạy được 10km", priority="low")
    laws = _v2("set_priority_existing", [_model_line()], detail=detail, opening=opening, closing=closing)
    assert laws["store"] == "fail"


def test_set_effort_existing_tool_passes() -> None:
    laws = _v2(
        "set_effort_existing",
        [_model_line(), _tool("get_plan_detail", {}), _tool("set_subtask_effort", {"effort": "L"})],
    )
    assert laws["tool"] == "pass"


def test_set_effort_existing_tool_fails() -> None:
    laws = _v2("set_effort_existing", [_model_line(), _tool("set_plan_priority", {})])
    assert laws["tool"] == "fail"


def test_set_effort_existing_store_passes() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy được 10km", _item("Chạy 6km không nghỉ"), _item("Chạy 10km không nghỉ")))
    closing = _image(
        _one("Chạy được 10km", _item("Chạy 6km không nghỉ"), _item("Chạy 10km không nghỉ", effort="L"))
    )
    detail = Expectation(
        kind="set_effort_existing",
        goal="Chạy được 10km",
        title="Chạy 10km không nghỉ",
        effort="L",
    )
    laws = _v2("set_effort_existing", [_model_line()], detail=detail, opening=opening, closing=closing)
    assert laws["store"] == "pass"


def test_set_effort_existing_store_fails() -> None:
    from evals.model import Expectation

    opening = _image(_one("Chạy được 10km", _item("Chạy 10km không nghỉ")))
    closing = _image(_one("Chạy được 10km", _item("Chạy 10km không nghỉ", effort="L"), priority="low"))
    detail = Expectation(
        kind="set_effort_existing",
        goal="Chạy được 10km",
        title="Chạy 10km không nghỉ",
        effort="L",
    )
    laws = _v2("set_effort_existing", [_model_line()], detail=detail, opening=opening, closing=closing)
    assert laws["store"] == "fail"


def test_load_refusal_store_passes() -> None:
    """Ca từ chối đạt khi kho sau lượt hai bằng kho lúc mở."""

    from evals.model import Expectation

    opening = _image(_one("Đầy", _item("Sẵn", "pending", "2026-11-19", "L")))
    detail = Expectation(kind="load_refusal", note="12 giờ trên quỹ 8 giờ")
    laws = _score(
        "quét tải: từ chối",
        "Lần này chưa ghi. Ngày 19/11 sẽ có 12 giờ trên quỹ 8 giờ.",
        [_model_line()],
        cases_version=3,
        detail=detail,
        opening=opening,
        closing=opening,
    )
    assert laws["store"] == "pass"


def test_load_refusal_store_fails() -> None:
    """Ca từ chối trượt khi kho đổi, kể cả khi lời gọi có confirm true."""

    from evals.model import Expectation

    opening = _image(_one("Đầy", _item("Sẵn", "pending", "2026-11-19", "L")))
    closing = _image(
        _one(
            "Đầy",
            _item("Sẵn", "pending", "2026-11-19", "L"),
            _item("Thêm", "pending", "2026-11-19", "L"),
        )
    )
    detail = Expectation(kind="load_refusal", note="12 giờ trên quỹ 8 giờ")
    laws = _score(
        "quét tải: từ chối",
        "Lần này chưa ghi. Ngày 19/11 sẽ có 12 giờ trên quỹ 8 giờ.",
        [
            _model_line(),
            _tool("add_subtask", {"plan_id": "p", "title": "Thêm", "confirm": True}),
        ],
        cases_version=3,
        detail=detail,
        opening=opening,
        closing=closing,
    )
    assert laws["store"] == "fail"


def test_load_over_budget_store_ignores_confirm() -> None:
    """Cờ confirm true không làm ca vượt quỹ trượt khi kho không đổi."""

    from evals.model import Expectation

    opening = _image(_one("Đầy", _item("Sẵn", "pending", "2026-11-19", "L")))
    detail = Expectation(kind="load_over_budget", goal="Đầy", note="12 giờ trên quỹ 8 giờ")
    laws = _score(
        "quét tải: vượt quỹ",
        "Lần này chưa ghi. Ngày 19/11 sẽ có 12 giờ trên quỹ 8 giờ.",
        [
            _model_line(),
            _tool(
                "add_subtask",
                {"plan_id": "p", "title": "Thêm", "scheduled_on": "2026-11-19", "effort": "L", "confirm": True},
            ),
        ],
        cases_version=3,
        detail=detail,
        opening=opening,
        closing=opening,
    )
    assert laws["store"] == "pass"
