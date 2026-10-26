"""Adapter Anthropic. Chỗ duy nhất của lát này import SDK."""

from anthropic import AsyncAnthropic

from core.llm import ModelError, ModelRequest, ModelResponse, ToolRequest

_MODEL = "claude-haiku-5-5"
_MAX_TOKENS = 2048


class AnthropicModel:
    """Cổng Anthropic. Mỗi complete mở một client rồi đóng kết nối."""

    @property
    def model(self) -> str:
        """Tên model cố định. Không gán được từ bên ngoài."""

        return _MODEL

    async def complete(
        self,
        request: ModelRequest,
        *,
        api_key: str,
        timeout: float,
    ) -> ModelResponse:
        """Gọi messages.create một lần và dịch phản hồi sang cổng."""

        try:
            async with AsyncAnthropic(
                api_key=api_key,
                timeout=timeout,
                max_retries=0,
                base_url="https://api.anthropic.com",
            ) as client:
                message = await client.messages.create(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    thinking={"type": "disabled"},
                    system=request.system,
                    tools=_tools(request),
                    messages=_messages(request),
                )
        except Exception as error:
            raise ModelError(type(error).__name__) from None
        return _response(message)


def _tools(request: ModelRequest) -> list[dict[str, object]]:
    """Đưa catalog cổng thành danh sách tool của SDK, giữ thứ tự."""

    return [
        {
            "name": name,
            "description": spec["description"],
            "input_schema": spec["input_schema"],
        }
        for name, spec in request.tools.items()
    ]


def _messages(request: ModelRequest) -> list[dict[str, object]]:
    """Lịch sử văn bản, rồi mỗi vòng: khối tool rồi khối kết quả."""

    messages: list[dict[str, object]] = [
        {"role": message.role, "content": message.text} for message in request.messages
    ]
    for requests, results in request.rounds:
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": item.id,
                        "name": item.name,
                        "input": item.tool_input,
                    }
                    for item in requests
                ],
            }
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": item.tool_use_id,
                        "content": item.output,
                        "is_error": item.is_error,
                    }
                    for item in results
                ],
            }
        )
    return messages


def _response(message: object) -> ModelResponse:
    """Dịch message SDK. Chỉ nhận tool khi stop_reason là tool_use."""

    stop_reason = getattr(message, "stop_reason", None)
    if not isinstance(stop_reason, str):
        stop_reason = None
    text, tool_requests = _content(getattr(message, "content", ()), stop_reason)
    usage = getattr(message, "usage", None)
    return ModelResponse(
        text=text,
        tool_requests=tool_requests,
        stop_reason=stop_reason,
        input_tokens=_token(usage, "input_tokens"),
        output_tokens=_token(usage, "output_tokens"),
        model=_model_name(message),
    )


def _content(
    content: object,
    stop_reason: str | None,
) -> tuple[str, tuple[ToolRequest, ...]]:
    """Nối phần text. Khối tool chỉ thành ToolRequest khi stop_reason là tool_use."""

    texts: list[str] = []
    requests: list[ToolRequest] = []
    for block in content if isinstance(content, (list, tuple)) else ():
        kind = getattr(block, "type", None)
        if kind == "text":
            text = getattr(block, "text", "")
            if isinstance(text, str):
                texts.append(text)
        elif stop_reason == "tool_use" and kind == "tool_use":
            request = _tool_request(block)
            if request is not None:
                requests.append(request)
    return "".join(texts), tuple(requests)


def _tool_request(block: object) -> ToolRequest | None:
    """Nhận khối khi đủ id, tên và input là dict. Khối thiếu thì bỏ."""

    tool_id = getattr(block, "id", None)
    name = getattr(block, "name", None)
    tool_input = getattr(block, "input", None)
    if isinstance(tool_id, str) and isinstance(name, str) and isinstance(tool_input, dict):
        return ToolRequest(id=tool_id, name=name, tool_input=tool_input)
    return None


def _token(usage: object, name: str) -> int | None:
    """Token là số nguyên. Thiếu hoặc sai kiểu thì trống."""

    if usage is None:
        return None
    value = getattr(usage, name, None)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _model_name(message: object) -> str:
    """Tên model của phản hồi. Thiếu thì dùng tên adapter."""

    model = getattr(message, "model", None)
    if isinstance(model, str):
        return model
    return _MODEL
