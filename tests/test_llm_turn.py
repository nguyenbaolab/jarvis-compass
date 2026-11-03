"""Lượt gọi mô hình: client giả, không mở mạng."""

import asyncio
import json
import time

import pytest

from core.llm import ModelError, ModelResponse, TextMessage, ToolRequest
from core.plans import Plan, PlanConflictError, Subtask, SubtaskStatus
from core.system_prompt import PROMPT_VERSION, SYSTEM_PROMPT
from tests.helpers import MemoryPlanStore
from tools.saved_reply import REJECTED_SENTENCE
from tools.tool_definitions import DEFINITIONS_VERSION, TOOL_DEFINITIONS
from turns.llm_turn import run_turn

_MODEL_ERROR = "Chưa liên lạc được để trả lời lúc này."
_CAP = "Chưa trả lời xong yêu cầu này."
_MISSING = "Thiếu ANTHROPIC_API_KEY."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_LOG_KEYS = (
    "model",
    "prompt_version",
    "definitions_version",
    "stop_reason",
    "input_tokens",
    "output_tokens",
    "duration_ms",
    "error_type",
)


class BoomIfCalled(MemoryPlanStore):
    """Kho báo lỗi nếu lượt đụng vào."""

    async def add(self, goal: str, subtasks: tuple) -> object:
        raise AssertionError("kho bị gọi")

    async def list_newest_first(self) -> tuple:
        raise AssertionError("kho bị gọi")

    async def get(self, plan_id: str) -> object:
        raise AssertionError("kho bị gọi")

    async def replace(self, plan: object) -> None:
        raise AssertionError("kho bị gọi")


class FakeClient:
    """Cổng giả: trả lần lượt các phản hồi hoặc ném lỗi đã xếp."""

    def __init__(self, scripted: list[object], model: str = "client-model") -> None:
        self.model = model
        self._scripted = list(scripted)
        self.calls: list[tuple[object, str, float]] = []

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        self.calls.append((request, api_key, timeout))
        item = self._scripted.pop(0)
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, ModelResponse)
        return item


def _reply(
    text: str,
    stop_reason: str | None,
    tools: tuple[ToolRequest, ...] = (),
    model: str = "response-model",
) -> ModelResponse:
    return ModelResponse(
        text=text,
        tool_requests=tools,
        stop_reason=stop_reason,
        input_tokens=3,
        output_tokens=4,
        model=model,
    )


def _tool(tool_id: str, name: str, tool_input: dict[str, object]) -> ToolRequest:
    return ToolRequest(id=tool_id, name=name, tool_input=tool_input)


def _run(
    message: str,
    history: list[TextMessage],
    client: FakeClient,
    store: MemoryPlanStore,
    api_key: str | None,
    log: list[str],
) -> str:
    return asyncio.run(
        run_turn(
            message,
            history,
            store=store,
            api_key=api_key,
            client=client,
            log=log.append,
        )
    )


def _objects(lines: list[str]) -> list[dict[str, object]]:
    return [json.loads(line) for line in lines]


def test_text_reply_does_not_call_store(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    async def fake_execute(
        name: object,
        tool_input: object,
        *,
        store: object,
        log: object = None,
        remaining: object = None,
    ) -> object:
        calls.append(name)
        return type("Result", (), {"success": True, "output": ""})()

    monkeypatch.setattr("turns.llm_turn.execute_tool", fake_execute)
    client = FakeClient([_reply("Bạn muốn mình lập kế hoạch cho hai việc đó không?", "end_turn")])
    result = _run(
        "Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3",
        [],
        client,
        MemoryPlanStore(),
        "caller-key",
        [],
    )
    assert result == "Bạn muốn mình lập kế hoạch cho hai việc đó không?"
    assert len(client.calls) == 1
    assert len(calls) == 0


def test_history_order_is_kept_and_not_mutated() -> None:
    history = [
        TextMessage(role="user", text="tin cũ"),
        TextMessage(role="assistant", text="trả lời cũ"),
    ]
    snapshot = list(history)
    client = FakeClient([_reply("xong", "end_turn")])
    _run("tin mới", history, client, MemoryPlanStore(), "caller-key", [])
    assert history == snapshot
    request = client.calls[0][0]
    assert request.messages == (
        TextMessage(role="user", text="tin cũ"),
        TextMessage(role="assistant", text="trả lời cũ"),
        TextMessage(role="user", text="tin mới"),
    )


def test_empty_text_is_success() -> None:
    client = FakeClient([_reply("", "end_turn")])
    result = _run("xin chào", [], client, BoomIfCalled(), "caller-key", [])
    assert result == ""


def test_one_tool_then_text_forwards_output() -> None:
    logs: list[str] = []
    store = MemoryPlanStore()
    client = FakeClient(
        [
            _reply(
                "",
                "tool_use",
                (_tool("t1", "get_plans", {}),),
            ),
            _reply("Bạn đang có một kế hoạch.", "end_turn"),
        ]
    )
    result = _run("liệt kê", [], client, store, "caller-key", logs)
    assert result == "Bạn đang có một kế hoạch."
    assert len(client.calls) == 2
    _requests, results = client.calls[1][0].rounds[0]
    assert results[0].output != ""
    assert results[0].is_error is False
    kinds = ["tool" if "tool" in item else "model" for item in _objects(logs)]
    assert kinds == ["model", "tool", "model"]


def test_failed_tool_output_is_unchanged() -> None:
    client = FakeClient(
        [
            _reply(
                "",
                "tool_use",
                (_tool("t1", "get_plan_detail", {"plan_id": "khong-co"}),),
            ),
            _reply("Không thấy kế hoạch đó.", "end_turn"),
        ]
    )
    result = _run("mở", [], client, MemoryPlanStore(), "caller-key", [])
    assert result == "Không thấy kế hoạch đó."
    _requests, results = client.calls[1][0].rounds[0]
    assert results[0].output == _MISSING_PLAN
    assert results[0].is_error is True


def test_two_tools_in_one_response_both_run() -> None:
    client = FakeClient(
        [
            _reply(
                "",
                "tool_use",
                (
                    _tool("t1", "get_plans", {}),
                    _tool("t2", "get_plan_detail", {"plan_id": "khong-co"}),
                ),
            ),
            _reply("Đã xem cả hai.", "end_turn"),
        ]
    )
    result = _run("xem", [], client, MemoryPlanStore(), "caller-key", [])
    assert result == "Đã xem cả hai."
    assert len(client.calls) == 2
    requests, results = client.calls[1][0].rounds[0]
    assert [item.name for item in requests] == ["get_plans", "get_plan_detail"]
    assert results[0].tool_use_id == "t1"
    assert results[0].is_error is False
    assert results[1].tool_use_id == "t2"
    assert results[1].output == _MISSING_PLAN
    assert results[1].is_error is True


def test_fourth_round_runs_no_tools() -> None:
    scripted = [
        _reply("", "tool_use", (_tool(f"t{index}", "get_plans", {}),))
        for index in range(4)
    ]
    client = FakeClient(scripted)
    logs: list[str] = []
    result = _run("làm tiếp", [], client, MemoryPlanStore(), "caller-key", logs)
    assert result == _CAP
    assert len(client.calls) == 4
    tool_lines = [item for item in _objects(logs) if "tool" in item]
    assert len(tool_lines) == 3


def test_max_tokens_does_not_run_tools_and_logs_empty_error_type() -> None:
    logs: list[str] = []
    client = FakeClient(
        [
            _reply(
                "dở",
                "max_tokens",
                (_tool("t1", "get_plans", {}),),
                model="response-model",
            )
        ]
    )
    result = _run("kể việc", [], client, BoomIfCalled(), "caller-key", logs)
    assert result == _MODEL_ERROR
    assert len(client.calls) == 1
    assert len(logs) == 1
    logged = json.loads(logs[0])
    assert logged["stop_reason"] == "max_tokens"
    assert logged["error_type"] is None
    assert logged["model"] == "response-model"


def test_missing_or_empty_key_skips_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-secret-not-used")
    for api_key in (None, ""):
        client = FakeClient([_reply("không được gọi", "end_turn")])
        with pytest.raises(Exception) as caught:
            _run("xin chào", [], client, BoomIfCalled(), api_key, [])
        assert str(caught.value) == _MISSING
        assert client.calls == []
        assert "env-secret-not-used" not in str(caught.value)
    spaced = FakeClient([_reply("nhận khóa", "end_turn")])
    result = _run("xin chào", [], spaced, MemoryPlanStore(), "   ", [])
    assert result == "nhận khóa"
    assert spaced.calls[0][1] == "   "


def test_budget_stops_further_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    marks = iter((0.0, 21.0))
    monkeypatch.setattr("turns.llm_turn._now", lambda: next(marks))
    client = FakeClient([_reply("không gọi", "end_turn")])
    result = _run("xin chào", [], client, BoomIfCalled(), "caller-key", [])
    assert result == _MODEL_ERROR
    assert client.calls == []


def test_cancelled_error_propagates() -> None:
    client = FakeClient([asyncio.CancelledError()])
    logs: list[str] = []
    with pytest.raises(asyncio.CancelledError):
        _run("xin chào", [], client, MemoryPlanStore(), "caller-key", logs)
    assert logs == []


def test_model_error_hides_message() -> None:
    logs: list[str] = []
    client = FakeClient(
        [RuntimeError("secret-key-value http://example.invalid 429")],
        model="client-model",
    )
    result = _run("xin chào", [], client, BoomIfCalled(), "caller-key", logs)
    assert result == _MODEL_ERROR
    assert "secret-key-value" not in result
    assert "http://example.invalid" not in result
    assert "429" not in result
    assert len(client.calls) == 1
    logged = json.loads(logs[0])
    assert logged["model"] == "client-model"
    assert logged["error_type"] == "RuntimeError"
    assert "secret-key-value" not in logs[0]
    assert "http://example.invalid" not in logs[0]


def test_success_log_has_eight_keys_and_keeps_vietnamese() -> None:
    logs: list[str] = []
    client = FakeClient([_reply("Ổn.", "end_turn", model="response-model")])
    _run("Học tiếng Nhật", [], client, BoomIfCalled(), "caller-key", logs)
    assert len(logs) == 1
    assert "\\u" not in logs[0]
    logged = json.loads(logs[0])
    assert list(logged) == list(_LOG_KEYS)
    assert logged["model"] == "response-model"
    assert logged["prompt_version"] == PROMPT_VERSION
    assert isinstance(logged["prompt_version"], int)
    assert logged["definitions_version"] == DEFINITIONS_VERSION
    assert isinstance(logged["definitions_version"], int)
    assert logged["error_type"] is None
    assert isinstance(logged["duration_ms"], int)
    assert logged["duration_ms"] >= 0
    assert logs[0] == json.dumps(logged, ensure_ascii=False)


def test_log_failure_still_returns_text() -> None:
    def fail(line: str) -> None:
        raise OSError(line)

    client = FakeClient([_reply("vẫn trả", "end_turn")])
    result = asyncio.run(
        run_turn(
            "xin chào",
            [],
            store=BoomIfCalled(),
            api_key="caller-key",
            client=client,
            log=fail,
        )
    )
    assert result == "vẫn trả"


def test_each_call_sends_prompt_and_catalog() -> None:
    client = FakeClient(
        [
            _reply("", "tool_use", (_tool("t1", "get_plans", {}),)),
            _reply("xong", "end_turn"),
        ]
    )
    _run("xem", [], client, MemoryPlanStore(), "caller-key", [])
    assert len(client.calls) == 2
    for request, _key, _timeout in client.calls:
        assert request.system == SYSTEM_PROMPT
        assert request.tools is TOOL_DEFINITIONS
        assert "revise_plan" not in request.tools
        assert len(request.tools) == 6


def _patch_clock(monkeypatch: pytest.MonkeyPatch, marks: tuple[float, ...]) -> None:
    values = iter(marks)
    monkeypatch.setattr("turns.llm_turn._now", lambda: next(values))


def test_budget_stops_second_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clock(monkeypatch, (0.0, 0.0, 0.0, 0.0, 0.0, 21.0))
    ran: list[object] = []

    async def fake_execute(
        name: object,
        tool_input: object,
        *,
        store: object,
        log: object = None,
        remaining: object = None,
    ) -> object:
        ran.append(name)
        return type("Result", (), {"success": True, "output": "ok"})()

    monkeypatch.setattr("turns.llm_turn.execute_tool", fake_execute)
    client = FakeClient(
        [
            _reply(
                "",
                "tool_use",
                (
                    _tool("t1", "get_plans", {}),
                    _tool("t2", "get_plan_detail", {"plan_id": "x"}),
                ),
            ),
            _reply("không được gọi lại", "end_turn"),
        ]
    )
    result = _run("xem", [], client, MemoryPlanStore(), "caller-key", [])
    assert ran == ["get_plans"]
    assert len(client.calls) == 1
    assert result == _MODEL_ERROR


def test_complete_timeout_is_remaining(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clock(monkeypatch, (0.0, 5.0, 8.0, 8.0))
    client = FakeClient([_reply("ok", "end_turn")])
    _run("xin chào", [], client, MemoryPlanStore(), "caller-key", [])
    assert client.calls[0][2] == 15


def test_budget_boundary_calls_complete_until_twenty(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clock(monkeypatch, (0.0, 19.9, 19.9, 19.9))
    early = FakeClient([_reply("còn kịp", "end_turn")])
    result = _run("xin chào", [], early, MemoryPlanStore(), "caller-key", [])
    assert len(early.calls) == 1
    assert early.calls[0][2] == 20 - 19.9
    assert result == "còn kịp"

    _patch_clock(monkeypatch, (0.0, 20.1))
    late = FakeClient([_reply("không", "end_turn")])
    result = _run("xin chào", [], late, MemoryPlanStore(), "caller-key", [])
    assert late.calls == []
    assert result == _MODEL_ERROR


def test_same_log_object_is_passed_to_execute_tool(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    received: list[object] = []

    async def fake_execute(
        name: object,
        tool_input: object,
        *,
        store: object,
        log: object = None,
        remaining: object = None,
    ) -> object:
        received.append(log)
        assert log is not None
        log("DÒNG-TOOL-GIẢ")
        return type("Result", (), {"success": True, "output": "ok"})()

    monkeypatch.setattr("turns.llm_turn.execute_tool", fake_execute)

    def caller_log(line: str) -> None:
        return None

    client = FakeClient(
        [
            _reply("", "tool_use", (_tool("t1", "get_plans", {}),)),
            _reply("xong", "end_turn"),
        ]
    )
    asyncio.run(
        run_turn(
            "xem",
            [],
            store=MemoryPlanStore(),
            api_key="caller-key",
            client=client,
            log=caller_log,
        )
    )
    assert received[0] is caller_log

    client = FakeClient(
        [
            _reply("", "tool_use", (_tool("t1", "get_plans", {}),)),
            _reply("xong", "end_turn"),
        ]
    )
    asyncio.run(
        run_turn(
            "xem",
            [],
            store=MemoryPlanStore(),
            api_key="caller-key",
            client=client,
            log=None,
        )
    )
    captured = capsys.readouterr().out
    assert "DÒNG-TOOL-GIẢ" in captured
    assert '"model"' in captured


def test_model_error_logs_class_name() -> None:
    logs: list[str] = []
    client = FakeClient([ModelError("APITimeoutError")], model="client-model")
    result = _run("xin chào", [], client, MemoryPlanStore(), "caller-key", logs)
    assert result == _MODEL_ERROR
    assert json.loads(logs[0])["error_type"] == "APITimeoutError"


def test_log_cancelled_propagates_and_oserror_keeps_model_error() -> None:
    def cancel(line: str) -> None:
        raise asyncio.CancelledError()

    client = FakeClient([_reply("xong", "end_turn")])
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            run_turn(
                "xin chào",
                [],
                store=MemoryPlanStore(),
                api_key="caller-key",
                client=client,
                log=cancel,
            )
        )

    def broken(line: str) -> None:
        raise OSError("log down")

    client = FakeClient([RuntimeError("boom")], model="client-model")
    result = asyncio.run(
        run_turn(
            "xin chào",
            [],
            store=MemoryPlanStore(),
            api_key="caller-key",
            client=client,
            log=broken,
        )
    )
    assert result == _MODEL_ERROR


def test_error_log_keeps_model_characters() -> None:
    logs: list[str] = []
    client = FakeClient([RuntimeError("boom")], model="mô-hình")
    result = asyncio.run(
        run_turn(
            "xin chào",
            [],
            store=MemoryPlanStore(),
            api_key="caller-key",
            client=client,
            log=logs.append,
        )
    )
    assert result == _MODEL_ERROR
    assert "mô-hình" in logs[0]


def test_duration_ms_uses_clock_around_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_clock(monkeypatch, (0.0, 0.0, 10.0, 11.5))
    logs: list[str] = []
    client = FakeClient([_reply("ok", "end_turn")])
    _run("xin chào", [], client, MemoryPlanStore(), "caller-key", logs)
    assert json.loads(logs[0])["duration_ms"] == 1500


def test_system_prompt_has_six_laws() -> None:
    assert PROMPT_VERSION == 2
    assert "get_plan_detail" not in SYSTEM_PROMPT
    assert "Friday" not in SYSTEM_PROMPT
    assert SYSTEM_PROMPT.count("trợ lý lập kế hoạch") == 1
    assert "Bạn là JARVIS. Không dùng tên nhân vật nào khác." in SYSTEM_PROMPT
    assert "Trả lời bằng tiếng Việt." in SYSTEM_PROMPT
    assert "Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3" in SYSTEM_PROMPT
    assert 'Không tự xưng "trợ lý lập kế hoạch".' in SYSTEM_PROMPT
    assert "Luật này không áp khi người dùng báo một việc đã xong hoặc bỏ" in SYSTEM_PROMPT
    assert "Không in đậm bằng **." in SYSTEM_PROMPT
    assert 'một dòng chữ trơn như "Ngày 1"' in SYSTEM_PROMPT
    assert "Tiêu đề việc con do bạn tự đặt không có tiền tố thứ tự" in SYSTEM_PROMPT
    assert 'không có tiền tố thứ tự như "Ngày 1:", "Tuần 1:", "Bước 1", "1."' in SYSTEM_PROMPT
    assert "Tiêu đề việc con do bạn tự đặt phải có điểm kết thúc đo được." in SYSTEM_PROMPT
    assert "Không tự đặt việc kiểu thói quen suốt một khoảng thời gian." in SYSTEM_PROMPT
    assert "Tiêu đề do người dùng tự đưa được giữ nguyên từng chữ." in SYSTEM_PROMPT
    assert "Không hiện mã kế hoạch hay mã việc con." in SYSTEM_PROMPT
    assert "Cần mã thì tự tìm bằng get_plans với tên việc." in SYSTEM_PROMPT
    assert "Không dùng pending, done, skipped trong câu trả lời." in SYSTEM_PROMPT
    assert "không phải chưa làm, xong, hay bỏ qua" in SYSTEM_PROMPT
    assert "gọi get_plans với tên việc họ nói" in SYSTEM_PROMPT
    assert "Khớp đúng một việc thì cập nhật ngay, không hỏi xác nhận." in SYSTEM_PROMPT
    assert "Không khớp hoặc khớp nhiều việc thì hỏi lại." in SYSTEM_PROMPT
    assert "Không đòi bằng chứng." in SYSTEM_PROMPT


def test_hung_store_returns_turn_inside_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    marks = iter((0.0, 0.0, 0.0, 0.0, 0.0, 19.95, 19.96, 19.97, 19.98, 19.99, 19.99))

    def _clock() -> float:
        try:
            return next(marks)
        except StopIteration:
            return 19.99

    monkeypatch.setattr("turns.llm_turn._now", _clock)

    class _HangAdd(MemoryPlanStore):
        async def add(self, goal: str, subtasks: tuple) -> object:
            await asyncio.Event().wait()
            raise AssertionError("không trả")

    client = FakeClient(
        [
            _reply("", "tool_use", (_tool("t1", "create_plan", {"goal": "Học tiếng Nhật"}),)),
            _reply("xong", "end_turn"),
        ]
    )

    async def _case() -> str:
        return await run_turn(
            "lập kế hoạch",
            [],
            store=_HangAdd(),
            api_key="caller-key",
            client=client,
            log=lambda _line: None,
        )

    result = asyncio.run(asyncio.wait_for(_case(), timeout=2))
    assert result == "xong"


class _StepClient:
    """Cổng giả nhận phản hồi hoặc hàm đọc request."""

    def __init__(self, steps: list[object]) -> None:
        self.model = "client-model"
        self.calls: list[tuple[object, str, float]] = []
        self._steps = list(steps)

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        self.calls.append((request, api_key, timeout))
        item = self._steps.pop(0)
        if callable(item):
            item = item(request)
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, ModelResponse)
        return item


def _create(goal: str, titles: list[str] | None = None) -> ModelResponse:
    tool_input: dict[str, object] = {"goal": goal}
    if titles is not None:
        tool_input["subtasks"] = titles
    return _reply("", "tool_use", (_tool("t-create", "create_plan", tool_input),))


def _turn(steps: list[object], store: MemoryPlanStore | None = None) -> str:
    client = _StepClient(steps)
    return asyncio.run(
        run_turn(
            "lập",
            [],
            store=MemoryPlanStore() if store is None else store,
            api_key="caller-key",
            client=client,
            log=lambda _line: None,
        )
    )


def test_saved_lines_replace_abnormal_endings(monkeypatch: pytest.MonkeyPatch) -> None:
    one = "1. Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana."
    two = "1. Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana, Mua vở."
    none = "1. Đã lưu kế hoạch Học tiếng Nhật."
    assert _turn([_create("Học tiếng Nhật", ["Học hiragana"]), _reply("", "end_turn")]) == one
    assert _turn([_create("Học tiếng Nhật", ["Học hiragana", "Mua vở"]), _reply("", "end_turn")]) == two
    assert _turn([_create("Học tiếng Nhật"), _reply("", "end_turn")]) == none

    def _add(request: object) -> ModelResponse:
        output = request.rounds[0][1][0].output
        plan_id = json.loads(output)["id"]
        return _reply("", "tool_use", (_tool("t-add", "add_subtask", {"plan_id": plan_id, "title": "Mua vở"}),))

    # Hai lần ghi: tạo không việc, rồi thêm việc. Dòng 1 là lần tạo.
    both = "1. Đã lưu kế hoạch Học tiếng Nhật.\n2. Đã lưu việc Mua vở vào kế hoạch Học tiếng Nhật."
    assert _turn([_create("Học tiếng Nhật"), _add, _reply("", "end_turn")]) == both

    def _status(request: object) -> ModelResponse:
        body = json.loads(request.rounds[0][1][0].output)
        return _reply(
            "",
            "tool_use",
            (
                _tool(
                    "t-status",
                    "update_subtask",
                    {
                        "plan_id": body["id"],
                        "subtask_id": body["subtasks"][0]["id"],
                        "status": "done",
                    },
                ),
            ),
        )

    status_line = "2. Đã lưu việc Học hiragana trong kế hoạch Học tiếng Nhật là xong."
    status_result = _turn([_create("Học tiếng Nhật", ["Học hiragana"]), _status, _reply("", "end_turn")])
    assert status_line in status_result
    assert "done" not in status_result
    assert "pending" not in status_result

    def _note(request: object) -> ModelResponse:
        body = json.loads(request.rounds[-1][1][0].output)
        return _reply(
            "",
            "tool_use",
            (
                _tool(
                    "t-note",
                    "set_subtask_note",
                    {
                        "plan_id": body["id"],
                        "subtask_id": body["subtasks"][0]["id"],
                        "note": "Đợi giáo trình",
                    },
                ),
            ),
        )

    def _clear(request: object) -> ModelResponse:
        body = json.loads(request.rounds[0][1][0].output)
        return _reply(
            "",
            "tool_use",
            (
                _tool(
                    "t-clear",
                    "set_subtask_note",
                    {"plan_id": body["id"], "subtask_id": body["subtasks"][0]["id"], "note": ""},
                ),
            ),
        )

    noted = _turn([_create("Học tiếng Nhật", ["Học hiragana"]), _note, _reply("", "end_turn")])
    assert "2. Đã lưu ghi chú Đợi giáo trình cho việc Học hiragana trong kế hoạch Học tiếng Nhật." in noted
    cleared = _turn([_create("Học tiếng Nhật", ["Học hiragana"]), _clear, _reply("", "end_turn")])
    assert "2. Đã bỏ ghi chú của việc Học hiragana trong kế hoạch Học tiếng Nhật." in cleared

    endings = (
        _reply("", "max_tokens"),
        RuntimeError("model down"),
        _reply("", "refusal"),
        _reply("   ", "end_turn"),
    )
    for ending in endings:
        assert _turn([_create("Học tiếng Nhật"), ending]) == none
    budget = iter((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 21.0))
    monkeypatch.setattr("turns.llm_turn._now", lambda: next(budget))
    assert _turn([_create("Học tiếng Nhật"), _reply("không tới", "end_turn")]) == none
    monkeypatch.setattr("turns.llm_turn._now", time.monotonic)
    assert _turn(
        [
            _create("Một"),
            _create("Hai"),
            _create("Ba"),
            _reply("", "tool_use", (_tool("t4", "get_plans", {}),)),
        ]
    ) == "1. Đã lưu kế hoạch Một.\n2. Đã lưu kế hoạch Hai.\n3. Đã lưu kế hoạch Ba."


def test_compose_order_saved_uncertain_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = {"n": 0}

    def _clock() -> float:
        ticks["n"] += 1
        if ticks["n"] < 6:
            return 0.0
        return 19.9 + (ticks["n"] - 6) * 0.001

    monkeypatch.setattr("turns.llm_turn._now", _clock)

    class _HangAdd(MemoryPlanStore):
        async def add(self, goal: str, subtasks: tuple) -> object:
            await asyncio.Event().wait()
            raise AssertionError("không trả")

    only_uncertain = asyncio.run(
        asyncio.wait_for(
            run_turn(
                "lập",
                [],
                store=_HangAdd(),
                api_key="caller-key",
                client=_StepClient([_create("Học tiếng Nhật"), RuntimeError("model down")]),
                log=lambda _line: None,
            ),
            timeout=2,
        )
    )
    assert only_uncertain == "Chưa chắc thay đổi đã được lưu."

    class _Conflict(MemoryPlanStore):
        async def replace(self, plan: object) -> None:
            raise PlanConflictError()

    seeded = _Conflict()
    seeded._plans.append(
        Plan(
            id="11111111-1111-4111-8111-111111111111",
            goal="Học tiếng Nhật",
            subtasks=(
                Subtask(
                    id="22222222-2222-4222-8222-222222222222",
                    title="Học hiragana",
                    status=SubtaskStatus.PENDING,
                    note=None,
                ),
            ),
            created_order=1,
            version=0,
        )
    )
    only_rejected = _turn(
        [
            _reply(
                "",
                "tool_use",
                (_tool("t", "add_subtask", {"plan_id": seeded._plans[0].id, "title": "Mua vở"}),),
            ),
            RuntimeError("model down"),
        ],
        seeded,
    )
    assert only_rejected == "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."

    for blank in ("", "   "):
        ticks["n"] = 0
        abandoned_blank = asyncio.run(
            asyncio.wait_for(
                run_turn(
                    "lập",
                    [],
                    store=_HangAdd(),
                    api_key="caller-key",
                    client=_StepClient([_create("Học tiếng Nhật"), _reply(blank, "end_turn")]),
                    log=lambda _line: None,
                ),
                timeout=2,
            )
        )
        assert abandoned_blank == "Chưa chắc thay đổi đã được lưu."
        ticks["n"] = 0
        rejected_store = _Conflict()
        rejected_store._plans.append(
            Plan(
                id="11111111-1111-4111-8111-111111111111",
                goal="Học tiếng Nhật",
                subtasks=(
                    Subtask(
                        id="22222222-2222-4222-8222-222222222222",
                        title="Học hiragana",
                        status=SubtaskStatus.PENDING,
                        note=None,
                    ),
                ),
                created_order=1,
                version=0,
            )
        )
        rejected_blank = _turn(
            [
                _reply(
                    "",
                    "tool_use",
                    (
                        _tool(
                            "t",
                            "add_subtask",
                            {"plan_id": rejected_store._plans[0].id, "title": "Mua vở"},
                        ),
                    ),
                ),
                _reply(blank, "end_turn"),
            ],
            rejected_store,
        )
        assert rejected_blank == "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."

    class _HangReplace(MemoryPlanStore):
        async def replace(self, plan: object) -> None:
            await asyncio.Event().wait()

    def _add(request: object) -> ModelResponse:
        plan_id = json.loads(request.rounds[0][1][0].output)["id"]
        return _reply("", "tool_use", (_tool("t-add", "add_subtask", {"plan_id": plan_id, "title": "Mua vở"}),))

    ticks["n"] = 0
    saved_then_uncertain = asyncio.run(
        asyncio.wait_for(
            run_turn(
                "lập",
                [],
                store=_HangReplace(),
                api_key="caller-key",
                client=_StepClient([_create("Học tiếng Nhật"), _add, RuntimeError("model down")]),
                log=lambda _line: None,
            ),
            timeout=2,
        )
    )
    assert saved_then_uncertain == (
        "1. Đã lưu kế hoạch Học tiếng Nhật.\nChưa chắc thay đổi đã được lưu."
    )
    ticks["n"] = 0
    saved_abandoned_blank = asyncio.run(
        asyncio.wait_for(
            run_turn(
                "lập",
                [],
                store=_HangReplace(),
                api_key="caller-key",
                client=_StepClient([_create("Học tiếng Nhật"), _add, _reply("", "end_turn")]),
                log=lambda _line: None,
            ),
            timeout=2,
        )
    )
    assert saved_abandoned_blank == (
        "1. Đã lưu kế hoạch Học tiếng Nhật.\nChưa chắc thay đổi đã được lưu."
    )

    class _ConflictReplace(MemoryPlanStore):
        async def replace(self, plan: object) -> None:
            raise PlanConflictError()

    ticks["n"] = 0
    saved_then_rejected = _turn(
        [_create("Học tiếng Nhật"), _add, RuntimeError("model down")],
        _ConflictReplace(),
    )
    assert saved_then_rejected == (
        "1. Đã lưu kế hoạch Học tiếng Nhật.\n"
        "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."
    )

    class _HangThenConflict(MemoryPlanStore):
        def __init__(self) -> None:
            super().__init__()
            self.replaces = 0

        async def replace(self, plan: object) -> None:
            self.replaces += 1
            if self.replaces == 1:
                await asyncio.Event().wait()
            raise PlanConflictError()

    def _add_again(request: object) -> ModelResponse:
        plan_id = json.loads(request.rounds[0][1][0].output)["id"]
        return _reply(
            "",
            "tool_use",
            (_tool("t-add-2", "add_subtask", {"plan_id": plan_id, "title": "Nghe hội thoại"}),),
        )

    ticks["n"] = 0
    all_three = asyncio.run(
        asyncio.wait_for(
            run_turn(
                "lập",
                [],
                store=_HangThenConflict(),
                api_key="caller-key",
                client=_StepClient(
                    [_create("Học tiếng Nhật"), _add, _add_again, RuntimeError("model down")]
                ),
                log=lambda _line: None,
            ),
            timeout=2,
        )
    )
    assert all_three == (
        "1. Đã lưu kế hoạch Học tiếng Nhật.\n"
        "Chưa chắc thay đổi đã được lưu.\n"
        "Thay đổi chưa được áp dụng. Bạn thử lại giúp mình."
    )
    assert "\n\n" not in all_three


def test_model_text_and_tool_message_stay_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _turn([_create("Học tiếng Nhật"), _reply("Đã xong việc này.", "end_turn")]) == "Đã xong việc này."
    assert _turn([_reply("", "end_turn")]) == ""
    assert _turn([_reply("   ", "end_turn")]) == "   "
    marks = iter((0.0, 21.0))
    monkeypatch.setattr("turns.llm_turn._now", lambda: next(marks))
    assert _turn([_reply("không gọi", "end_turn")]) == _MODEL_ERROR
    monkeypatch.setattr("turns.llm_turn._now", time.monotonic)
    assert (
        _turn(
            [
                _reply("", "tool_use", (_tool("t1", "get_plans", {}),)),
                _reply("", "tool_use", (_tool("t2", "get_plans", {}),)),
                _reply("", "tool_use", (_tool("t3", "get_plans", {}),)),
                _reply("", "tool_use", (_tool("t4", "get_plans", {}),)),
            ]
        )
        == _CAP
    )

    ticks = {"n": 0}

    def _clock() -> float:
        ticks["n"] += 1
        if ticks["n"] < 6:
            return 0.0
        return 19.9 + (ticks["n"] - 6) * 0.001

    monkeypatch.setattr("turns.llm_turn._now", _clock)

    class _HangAdd(MemoryPlanStore):
        async def add(self, goal: str, subtasks: tuple) -> object:
            await asyncio.Event().wait()
            raise AssertionError("không trả")

    client = _StepClient(
        [
            _create("Học tiếng Nhật"),
            _reply("vẫn là chữ của mô hình", "end_turn"),
        ]
    )
    result = asyncio.run(
        asyncio.wait_for(
            run_turn(
                "lập",
                [],
                store=_HangAdd(),
                api_key="caller-key",
                client=client,
                log=lambda _line: None,
            ),
            timeout=2,
        )
    )
    assert result == "vẫn là chữ của mô hình"
    message = client.calls[1][0].rounds[0][1][0]
    assert message.output == "Chưa chắc thay đổi đã được lưu."
    assert message.__dataclass_fields__.keys() == {"tool_use_id", "output", "is_error"}


def test_rejected_sentence_reaches_the_next_model_round() -> None:
    class _Conflict(MemoryPlanStore):
        async def replace(self, plan: object) -> None:
            raise PlanConflictError()

    store = _Conflict()
    store._plans.append(
        Plan(
            id="11111111-1111-4111-8111-111111111111",
            goal="Học tiếng Nhật",
            subtasks=(
                Subtask(
                    id="22222222-2222-4222-8222-222222222222",
                    title="Học hiragana",
                    status=SubtaskStatus.PENDING,
                    note=None,
                ),
            ),
            created_order=1,
            version=0,
        )
    )
    client = _StepClient(
        [
            _reply(
                "",
                "tool_use",
                (
                    _tool(
                        "t",
                        "add_subtask",
                        {"plan_id": store._plans[0].id, "title": "Mua vở"},
                    ),
                ),
            ),
            _reply("Bạn thử lại giúp mình.", "end_turn"),
        ]
    )
    result = asyncio.run(
        run_turn(
            "lập",
            [],
            store=store,
            api_key="caller-key",
            client=client,
            log=lambda _line: None,
        )
    )
    assert result == "Bạn thử lại giúp mình."
    message = client.calls[1][0].rounds[0][1][0]
    assert message.output == REJECTED_SENTENCE
    assert message.is_error is True


def test_cancel_after_saved_write_propagates() -> None:
    with pytest.raises(asyncio.CancelledError):
        _turn([_create("Học tiếng Nhật"), asyncio.CancelledError()])

