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
