"""Ba lần và phân loại lỗi chạy. Client giả, không mở mạng."""

import asyncio
import json
import socket
from collections.abc import Coroutine
from typing import TypeVar

import pytest

from core.llm import ModelError, ModelRequest, ModelResponse, ToolRequest
from evals.model import Case, Dataset, Expectation, Group, PlanSeed, SubtaskSeed
from evals.store import build_store
from evals.summary import summarize
from evals.turn import ERROR_KINDS, RUNS_PER_CASE, TOOL_ROUND_CAP, run_cases, run_once
from tests.fakes.memory_plan_store import MemoryPlanStore

_T = TypeVar("_T")
_SOCKET_CALLS = {"n": 0}
_MODEL_ERROR_TEXT = "Chưa liên lạc được để trả lời lúc này."


def last_socket_calls() -> int:
    """Số lần socket.socket bị gọi trong lần run_offline gần nhất."""

    return _SOCKET_CALLS["n"]


def run_offline(coro: Coroutine[object, object, _T]) -> _T:
    """Tạo loop trước, rồi đếm và chặn socket, chạy, gỡ bịt, rồi đóng loop."""

    loop = asyncio.new_event_loop()
    _SOCKET_CALLS["n"] = 0

    def blocked(*args: object, **kwargs: object) -> object:
        del args, kwargs
        _SOCKET_CALLS["n"] += 1
        raise AssertionError("socket bị gọi")

    patch = pytest.MonkeyPatch()
    patch.setattr(socket, "socket", blocked)
    try:
        return loop.run_until_complete(coro)
    finally:
        patch.undo()
        loop.close()


class FakeClient:
    """Trả lần lượt các phản hồi, hoặc ném lỗi."""

    model = "claude-haiku-5-5"

    def __init__(self, steps: list[object]) -> None:
        self.steps = list(steps)
        self.requests: list[ModelRequest] = []

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del api_key, timeout
        assert isinstance(request, ModelRequest)
        self.requests.append(request)
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        assert isinstance(step, ModelResponse)
        return step


class WriteFlowClient:
    """get_plans rồi tool ghi, hoặc chỉ get_plans rồi kết thúc."""

    model = "claude-haiku-5-5"

    def __init__(self, *, tool: str, tool_input: dict[str, object], do_write: bool) -> None:
        self.tool = tool
        self.tool_input = tool_input
        self.do_write = do_write
        self.requests: list[ModelRequest] = []

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del api_key, timeout
        assert isinstance(request, ModelRequest)
        self.requests.append(request)
        if not request.rounds:
            return _reply("tool_use", (ToolRequest(id="g", name="get_plans", tool_input={}),))
        if self.do_write and len(request.rounds) == 1:
            plans = json.loads(request.rounds[-1][1][0].output)["plans"]
            plan = plans[0]
            payload = dict(self.tool_input)
            payload["plan_id"] = plan["id"]
            if self.tool != "add_subtask":
                payload["subtask_id"] = plan["subtasks"][0]["id"]
            return _reply("tool_use", (ToolRequest(id="w", name=self.tool, tool_input=payload),))
        return _reply("end_turn")


def _reply(stop_reason: str, tools: tuple[ToolRequest, ...] = (), text: str = "Mình nghe.") -> ModelResponse:
    return ModelResponse(
        text=text,
        tool_requests=tools,
        stop_reason=stop_reason,
        input_tokens=2,
        output_tokens=3,
        model="claude-haiku-5-5",
    )


def _case(group: Group = Group.CHI_KE_VIEC) -> Case:
    kind = "one_create_plan" if group == Group.LAP_KE_HOACH else "no_tool"
    return Case(
        id="c1",
        group=group,
        user_message="kể",
        dataset="",
        expectation=Expectation(kind=kind),
    )


def _write_dataset() -> Dataset:
    return Dataset(
        name="kho",
        plans=(
            PlanSeed(
                goal="Đọc sách",
                subtasks=(SubtaskSeed(title="Chương 1", status="pending", note=None),),
            ),
        ),
    )


def test_offline_guard_blocks_socket() -> None:
    """Coroutine gọi socket.socket qua helper thì số lần gọi tăng và AssertionError nổi lên."""

    async def call_socket() -> None:
        socket.socket()

    with pytest.raises(AssertionError):
        run_offline(call_socket())
    assert last_socket_calls() == 1


def _assert_no_socket() -> None:
    assert last_socket_calls() == 0


def test_run_error_missing_key() -> None:
    """Thiếu khóa là missing_key và lần sau vẫn chạy."""

    first = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient([_reply("end_turn")]), ""))
    assert first.kind == "missing_key"
    _assert_no_socket()
    second = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient([_reply("end_turn")]), "k"))
    assert second.kind == "scored"
    _assert_no_socket()


def test_run_error_no_model_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hết ngân sách trước complete không có dòng tám khóa."""

    monkeypatch.setattr("turns.llm_turn._remaining", lambda started: 0)
    outcome = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient([_reply("end_turn")]), "k"))
    assert outcome.kind == "no_model_log"
    _assert_no_socket()


def test_run_error_ended_on_tool_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hết ngân sách sau một tool để dòng cuối là dòng bảy khóa."""

    calls = {"n": 0}

    def remaining(started: float) -> float:
        del started
        calls["n"] += 1
        return 0 if calls["n"] >= 3 else 10

    monkeypatch.setattr("turns.llm_turn._remaining", remaining)
    tools = (
        ToolRequest(id="a", name="get_plans", tool_input={}),
        ToolRequest(id="b", name="get_plans", tool_input={}),
    )
    outcome = run_offline(
        run_once(_case(), MemoryPlanStore(), FakeClient([_reply("tool_use", tools)]), "k")
    )
    assert outcome.kind == "ended_on_tool_log"
    _assert_no_socket()


def test_run_error_model_error() -> None:
    """error_type khác null là model_error."""

    outcome = run_offline(
        run_once(_case(), MemoryPlanStore(), FakeClient([ModelError("TimeoutError")]), "k")
    )
    assert outcome.kind == "model_error"
    _assert_no_socket()


def test_run_error_bad_stop_reason_max_tokens() -> None:
    """max_tokens là bad_stop_reason."""

    outcome = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient([_reply("max_tokens")]), "k"))
    assert outcome.kind == "bad_stop_reason"
    _assert_no_socket()


def test_run_error_bad_stop_reason_tool_use_without_requests() -> None:
    """tool_use không có tool_requests khi chưa đủ ba vòng là bad_stop_reason."""

    outcome = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient([_reply("tool_use")]), "k"))
    assert outcome.kind == "bad_stop_reason"
    _assert_no_socket()


def test_cap_counted_outside_rate() -> None:
    """Hết lượt tool sau đúng ba vòng vẫn được chấm và được đếm riêng."""

    tool = ToolRequest(id="a", name="get_plans", tool_input={})
    steps: list[object] = [_reply("tool_use", (tool,)) for _ in range(3)]
    steps.append(_reply("tool_use", (tool,)))
    outcome = run_offline(run_once(_case(), MemoryPlanStore(), FakeClient(steps), "k"))
    assert outcome.kind == "cap"
    assert outcome.kind not in ERROR_KINDS
    assert outcome.laws is not None
    from evals.summary import RunRecord

    report = summarize(
        (
            RunRecord(
                case_id="c1",
                group="chỉ kể việc",
                index=1,
                kind=outcome.kind,
                reply=outcome.reply,
                lines=outcome.lines,
                rounds=outcome.rounds,
                laws=outcome.laws,
            ),
        )
    )
    assert report.by_case[0].run_errors == 0
    assert report.by_case[0].rate is not None
    assert report.by_case[0].cap_stops == 1
    _assert_no_socket()


def test_three_errors_leave_rate_empty_and_continue() -> None:
    """Ba lần lỗi chạy thì tỉ lệ null, run_errors là 3, câu sau vẫn chạy."""

    broken = Case(id="broken", group=Group.CHI_KE_VIEC, user_message="a", dataset="", expectation=Expectation(kind="no_tool"))
    later = Case(id="later", group=Group.CHI_KE_VIEC, user_message="b", dataset="", expectation=Expectation(kind="no_tool"))
    client = FakeClient([ModelError("TimeoutError") for _ in range(3)] + [_reply("end_turn")])
    batches = run_offline(run_cases((broken, later), client, "k", datasets={}))
    assert len(batches) == 2
    from evals.summary import RunRecord

    report = summarize(
        tuple(
            RunRecord(
                case_id="broken",
                group="chỉ kể việc",
                index=index,
                kind=run.kind,
                reply=run.reply,
                lines=run.lines,
                rounds=run.rounds,
                laws=run.laws,
            )
            for index, run in enumerate(batches[0], start=1)
        )
    )
    assert report.by_case[0].rate is None
    assert report.by_case[0].run_errors == 3
    assert batches[1][0].kind == "scored"
    _assert_no_socket()


def test_three_missing_key_through_run_cases() -> None:
    """Ba lần missing_key đi qua run_cases: tỉ lệ null, run_errors là 3."""

    case = Case(id="k", group=Group.CHI_KE_VIEC, user_message="a", dataset="", expectation=Expectation(kind="no_tool"))
    batches = run_offline(run_cases((case,), FakeClient([]), "", datasets={}))
    assert [run.kind for run in batches[0]] == ["missing_key", "missing_key", "missing_key"]
    from evals.summary import RunRecord

    report = summarize(
        tuple(
            RunRecord(
                case_id="k",
                group="chỉ kể việc",
                index=index,
                kind=run.kind,
                reply=run.reply,
                lines=run.lines,
                rounds=run.rounds,
                laws=run.laws,
            )
            for index, run in enumerate(batches[0], start=1)
        )
    )
    assert report.by_case[0].rate is None
    assert report.by_case[0].run_errors == 3
    _assert_no_socket()


def test_end_turn_with_model_error_text_is_scored() -> None:
    """end_turn, error_type null, text trùng câu lỗi phía mô hình vẫn là scored."""

    outcome = run_offline(
        run_once(
            _case(),
            MemoryPlanStore(),
            FakeClient([_reply("end_turn", text=_MODEL_ERROR_TEXT)]),
            "k",
        )
    )
    assert outcome.kind == "scored"
    assert outcome.reply == _MODEL_ERROR_TEXT
    _assert_no_socket()


def test_only_seven_key_lines_are_no_model_log() -> None:
    """Log chỉ gồm dòng bảy khóa, không có dòng tám khóa, là no_model_log."""

    from evals.turn import _kind_of

    tool_line = json.dumps(
        {
            "tool": "get_plans",
            "input": {},
            "ok": True,
            "error_type": None,
            "duration_ms": 1,
            "definitions_version": 1,
            "detail": None,
        }
    )
    assert _kind_of([tool_line]) == "no_model_log"


def test_store_law_through_run_once_for_write_groups() -> None:
    """run_once truyền kỳ vọng tới luật kho: mỗi nhóm ghi một ca đạt và một ca trượt."""

    dataset = _write_dataset()
    cases = (
        (
            Group.CAP_NHAT,
            Expectation(kind="update_status", goal="Đọc sách", title="Chương 1", status="done"),
            "update_subtask",
            {"status": "done"},
        ),
        (
            Group.THEM_VIEC,
            Expectation(kind="add_subtask", goal="Đọc sách", title="Chương mới"),
            "add_subtask",
            {"title": "Chương mới"},
        ),
        (
            Group.GHI_CHU,
            Expectation(kind="set_note", goal="Đọc sách", title="Chương 1", note="đã nộp"),
            "set_subtask_note",
            {"note": "đã nộp"},
        ),
    )
    for group, expectation, tool, tool_input in cases:
        case = Case(id=group.value, group=group, user_message="làm", dataset="kho", expectation=expectation)
        store = run_offline(build_store(dataset))
        passed = run_offline(
            run_once(
                case,
                store,
                WriteFlowClient(tool=tool, tool_input=tool_input, do_write=True),
                "k",
                dataset_titles=frozenset({"Chương 1"}),
            )
        )
        assert passed.kind == "scored"
        assert passed.laws is not None
        assert passed.laws["store"] == "pass"
        _assert_no_socket()
        failed_store = run_offline(build_store(dataset))
        failed = run_offline(
            run_once(
                case,
                failed_store,
                WriteFlowClient(tool=tool, tool_input=tool_input, do_write=False),
                "k",
                dataset_titles=frozenset({"Chương 1"}),
            )
        )
        assert failed.kind == "scored"
        assert failed.laws is not None
        assert failed.laws["store"] == "fail"
        _assert_no_socket()


def test_store_isolation_and_empty_history_each_run() -> None:
    """Lần một thêm việc con. Lần hai kho mới trùng bộ dữ liệu gốc. Request đầu mỗi lượt một tin user."""

    dataset = _write_dataset()
    case = Case(
        id="add",
        group=Group.THEM_VIEC,
        user_message="thêm",
        dataset="kho",
        expectation=Expectation(kind="add_subtask", goal="Đọc sách", title="Chương mới"),
    )
    first_client = WriteFlowClient(tool="add_subtask", tool_input={"title": "Chương mới"}, do_write=True)
    first_store = run_offline(build_store(dataset))
    first = run_offline(
        run_once(case, first_store, first_client, "k", dataset_titles=frozenset({"Chương 1"}))
    )
    assert first.laws is not None
    assert first.laws["store"] == "pass"
    after_first = run_offline(first_store.list_newest_first())
    assert [item.title for item in after_first[0].subtasks] == ["Chương 1", "Chương mới"]
    second_client = WriteFlowClient(tool="add_subtask", tool_input={"title": "Chương mới"}, do_write=True)
    second_store = run_offline(build_store(dataset))
    before_second = run_offline(second_store.list_newest_first())
    assert [item.title for item in before_second[0].subtasks] == ["Chương 1"]
    second = run_offline(
        run_once(case, second_store, second_client, "k", dataset_titles=frozenset({"Chương 1"}))
    )
    assert second.laws is not None
    assert second.laws["store"] == "pass"
    for client in (first_client, second_client):
        first_request = client.requests[0]
        assert len(first_request.rounds) == 0
        assert len(first_request.messages) == 1
        assert first_request.messages[0].role == "user"
    _assert_no_socket()


class AlwaysGetPlansClient:
    """Luôn trả tool_use với một get_plans, không cạn phản hồi."""

    model = "claude-haiku-5-5"

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del request, api_key, timeout
        return _reply("tool_use", (ToolRequest(id="g", name="get_plans", tool_input={}),))


def test_run_cases_on_case_done_reports_finished_cases_in_order() -> None:
    """Hai câu đủ lần thì on_case_done được gọi đúng hai lần, theo thứ tự, mỗi tuple dài RUNS_PER_CASE."""

    seen: list[tuple[int, int, str, tuple[str, ...]]] = []

    def record(done: int, total: int, case_id: str, kinds: tuple[str, ...]) -> None:
        seen.append((done, total, case_id, kinds))

    first = Case(
        id="id1",
        group=Group.CHI_KE_VIEC,
        user_message="a",
        dataset="",
        expectation=Expectation(kind="no_tool"),
    )
    second = Case(
        id="id2",
        group=Group.CHI_KE_VIEC,
        user_message="b",
        dataset="",
        expectation=Expectation(kind="no_tool"),
    )
    steps: list[object] = [_reply("end_turn") for _ in range(RUNS_PER_CASE * 2)]
    batches = run_offline(
        run_cases((first, second), FakeClient(steps), "k", datasets={}, on_case_done=record)
    )
    assert len(seen) == 2
    assert seen[0][:3] == (1, 2, "id1")
    assert seen[1][:3] == (2, 2, "id2")
    assert seen[0][3] == tuple(run.kind for run in batches[0])
    assert seen[1][3] == tuple(run.kind for run in batches[1])
    assert len(seen[0][3]) == RUNS_PER_CASE
    assert len(seen[1][3]) == RUNS_PER_CASE
    _assert_no_socket()


def test_run_once_always_get_plans_is_cap_at_tool_round_cap() -> None:
    """Client luôn trả tool_use get_plans thì kind là cap và rounds bằng TOOL_ROUND_CAP."""

    outcome = run_offline(run_once(_case(), MemoryPlanStore(), AlwaysGetPlansClient(), "k"))
    assert outcome.kind == "cap"
    assert outcome.rounds == TOOL_ROUND_CAP
    _assert_no_socket()
