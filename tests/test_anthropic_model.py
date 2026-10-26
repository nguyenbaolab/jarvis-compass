"""Adapter Anthropic: bịt SDK, không mở mạng, không đọc attribute riêng."""

import asyncio

import pytest

from clients.anthropic_model import AnthropicModel
from core.llm import (
    ModelError,
    ModelRequest,
    TextMessage,
    ToolRequest,
    ToolResultMessage,
)


class _Block:
    def __init__(self, **kwargs: object) -> None:
        self.__dict__.update(kwargs)


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Message:
    def __init__(self, content: list[object], stop_reason: str, model: str) -> None:
        self.content = content
        self.stop_reason = stop_reason
        self.model = model
        self.usage = _Usage(2, 3)


class _Messages:
    def __init__(self, scripted: list[object]) -> None:
        self._scripted = scripted
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        item = self._scripted.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _FakeAsync:
    init_kwargs: list[dict[str, object]] = []
    messages: list[_Messages] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        _FakeAsync.init_kwargs.append(kwargs)
        self.messages = _Messages(_FakeAsync.scripted)
        _FakeAsync.messages.append(self.messages)

    async def __aenter__(self) -> "_FakeAsync":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False


def _install(monkeypatch: pytest.MonkeyPatch, scripted: list[object]) -> None:
    _FakeAsync.init_kwargs = []
    _FakeAsync.messages = []
    _FakeAsync.scripted = scripted
    monkeypatch.setattr("clients.anthropic_model.AsyncAnthropic", _FakeAsync)


def _request() -> ModelRequest:
    return ModelRequest(
        system="prompt",
        messages=(TextMessage(role="user", text="xin chào"),),
        tools={
            "get_plans": {
                "description": "Liệt kê.",
                "input_schema": {"type": "object"},
            }
        },
        rounds=(),
    )


def _two_tool_request() -> ModelRequest:
    return ModelRequest(
        system="prompt",
        messages=(
            TextMessage(role="user", text="cũ"),
            TextMessage(role="assistant", text="đã nghe"),
        ),
        tools={
            "get_plans": {
                "description": "Liệt kê.",
                "input_schema": {"type": "object"},
            }
        },
        rounds=(
            (
                (
                    ToolRequest(id="a", name="get_plans", tool_input={}),
                    ToolRequest(id="b", name="get_plan_detail", tool_input={"plan_id": "p1"}),
                ),
                (
                    ToolResultMessage(tool_use_id="a", output="có một kế hoạch", is_error=False),
                    ToolResultMessage(
                        tool_use_id="b",
                        output="Không có kế hoạch với danh tính này.",
                        is_error=True,
                    ),
                ),
            ),
        ),
    )


def test_create_args_use_caller_key_and_disable_thinking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _Message([_Block(type="text", text="xong")], "end_turn", "claude-haiku-5-5")
    _install(monkeypatch, [message])
    result = asyncio.run(
        AnthropicModel().complete(_request(), api_key="caller-key", timeout=4.5)
    )
    assert result.text == "xong"
    assert result.stop_reason == "end_turn"
    assert result.model == "claude-haiku-5-5"
    assert result.input_tokens == 2
    assert result.output_tokens == 3
    assert _FakeAsync.init_kwargs == [
        {
            "api_key": "caller-key",
            "timeout": 4.5,
            "max_retries": 0,
            "base_url": "https://api.anthropic.com",
        }
    ]
    sent = _FakeAsync.messages[0].calls[0]
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["max_tokens"] == 2048
    assert sent["thinking"] == {"type": "disabled"}
    assert "stream" not in sent
    assert sent["system"] == "prompt"
    assert sent["tools"] == [
        {
            "name": "get_plans",
            "description": "Liệt kê.",
            "input_schema": {"type": "object"},
        }
    ]


def test_messages_include_history_then_two_tool_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _Message([_Block(type="text", text="xong")], "end_turn", "claude-haiku-5-5")
    _install(monkeypatch, [message])
    asyncio.run(
        AnthropicModel().complete(_two_tool_request(), api_key="caller-key", timeout=1.0)
    )
    sent = _FakeAsync.messages[0].calls[0]
    assert sent["messages"] == [
        {"role": "user", "content": "cũ"},
        {"role": "assistant", "content": "đã nghe"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "a", "name": "get_plans", "input": {}},
                {
                    "type": "tool_use",
                    "id": "b",
                    "name": "get_plan_detail",
                    "input": {"plan_id": "p1"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "a",
                    "content": "có một kế hoạch",
                    "is_error": False,
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "b",
                    "content": "Không có kế hoạch với danh tính này.",
                    "is_error": True,
                },
            ],
        },
    ]


def test_sdk_exception_becomes_model_error_without_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, [RuntimeError("secret-key-value http://example.invalid")])
    with pytest.raises(ModelError) as caught:
        asyncio.run(AnthropicModel().complete(_request(), api_key="caller-key", timeout=1.0))
    assert caught.value.class_name == "RuntimeError"
    assert "secret-key-value" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_cancelled_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, [asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(AnthropicModel().complete(_request(), api_key="caller-key", timeout=1.0))


def test_tool_use_blocks_keep_order_and_skip_non_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _Message(
        [
            _Block(type="tool_use", id="a", name="get_plans", input={}),
            _Block(type="tool_use", id="b", name="get_plan_detail", input={"plan_id": "p1"}),
            _Block(type="tool_use", id="c", name="get_plans", input="không phải dict"),
        ],
        "tool_use",
        "claude-haiku-5-5",
    )
    _install(monkeypatch, [message])
    result = asyncio.run(
        AnthropicModel().complete(_request(), api_key="caller-key", timeout=1.0)
    )
    assert result.tool_requests == (
        ToolRequest(id="a", name="get_plans", tool_input={}),
        ToolRequest(id="b", name="get_plan_detail", tool_input={"plan_id": "p1"}),
    )


def test_close_error_becomes_model_error(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _Message([_Block(type="text", text="xong")], "end_turn", "claude-haiku-5-5")
    _install(monkeypatch, [message])

    class _BoomExit(_FakeAsync):
        async def __aexit__(self, *_exc: object) -> bool:
            raise RuntimeError("close-failed")

    monkeypatch.setattr("clients.anthropic_model.AsyncAnthropic", _BoomExit)
    with pytest.raises(ModelError) as caught:
        asyncio.run(AnthropicModel().complete(_request(), api_key="caller-key", timeout=1.0))
    assert caught.value.class_name == "RuntimeError"
    assert caught.value.__suppress_context__ is True


def test_base_url_and_model_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _Message([_Block(type="text", text="xong")], "end_turn", "claude-haiku-5-5")
    _install(monkeypatch, [message])
    adapter = AnthropicModel()
    with pytest.raises(AttributeError):
        adapter.model = "other"
    asyncio.run(adapter.complete(_request(), api_key="caller-key", timeout=1.0))
    assert _FakeAsync.init_kwargs[0]["base_url"] == "https://api.anthropic.com"
    assert _FakeAsync.messages[0].calls[0]["model"] == "claude-haiku-5-5"


def test_non_tool_stop_drops_tool_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _Message(
        [
            _Block(type="tool_use", id="a", name="get_plans", input={"keyword": "x"}),
            _Block(type="text", text="dở"),
        ],
        "max_tokens",
        "claude-haiku-5-5",
    )
    _install(monkeypatch, [message])
    result = asyncio.run(
        AnthropicModel().complete(_request(), api_key="caller-key", timeout=1.0)
    )
    assert result.stop_reason == "max_tokens"
    assert result.tool_requests == ()
    assert result.text == "dở"
