"""Lượt gọi mô hình: client giả, không mở mạng."""

import asyncio
import json

import pytest

from core.llm import ModelError, ModelResponse, TextMessage, ToolRequest
from core.system_prompt import PROMPT_VERSION, SYSTEM_PROMPT
from tests.helpers import MemoryPlanStore
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

