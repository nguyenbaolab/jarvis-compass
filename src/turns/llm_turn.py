"""Một lượt: gọi cổng, chạy tool, rồi trả một chuỗi."""

import time
from collections.abc import Callable, Sequence

from core.llm import (
    ModelClient,
    ModelError,
    ModelRequest,
    ModelResponse,
    TextMessage,
    ToolRequest,
    ToolResultMessage,
)
from core.log_line import default_log, duration_ms, write_json_line
from core.plans import PlanStore
from core.system_prompt import PROMPT_VERSION, SYSTEM_PROMPT
from tools.tool_definitions import DEFINITIONS_VERSION, TOOL_DEFINITIONS
from tools.tool_router import execute_tool

_BUDGET_SECONDS = 20.0
_MAX_ROUNDS = 3
_MODEL_ERROR = "Chưa liên lạc được để trả lời lúc này."
_CAP = "Chưa trả lời xong yêu cầu này."
_MISSING_KEY = "Thiếu ANTHROPIC_API_KEY."


class MissingKeyError(Exception):
    """Khóa không được đưa. Câu lỗi không chứa giá trị khóa."""

    def __str__(self) -> str:
        return _MISSING_KEY


def _now() -> float:
    """Mốc thời gian đơn điệu. Test bịt hàm này, không bịt đồng hồ toàn cục."""

    return time.monotonic()


def _error_type(error: Exception) -> str:
    """Tên lớp để ghi log. ModelError dùng class_name, không dùng thông điệp."""

    if isinstance(error, ModelError):
        return error.class_name
    return type(error).__name__


def _model_log(
    log: Callable[[str], None],
    *,
    model: str,
    stop_reason: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: int,
    error_type: str | None,
) -> None:
    """Một dòng tám khóa, đúng thứ tự, cho một lần complete đã kết thúc."""

    write_json_line(
        log,
        {
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "definitions_version": DEFINITIONS_VERSION,
            "stop_reason": stop_reason,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "error_type": error_type,
        },
    )


def _remaining(started: float) -> float:
    """Phần ngân sách còn lại. Đọc đồng hồ đúng một lần."""

    return _BUDGET_SECONDS - (_now() - started)


async def _run_tools(
    requests: tuple[ToolRequest, ...],
    *,
    store: PlanStore,
    log: Callable[[str], None],
    started: float,
) -> tuple[ToolResultMessage, ...] | str:
    """Chạy mọi tool theo thứ tự. Hết giờ thì trả câu lỗi, không bắt đầu tool kế."""

    results: list[ToolResultMessage] = []
    for request in requests:
        if _remaining(started) <= 0:
            return _MODEL_ERROR
        tool_result = await execute_tool(
            request.name,
            request.tool_input,
            store=store,
            log=log,
        )
        results.append(
            ToolResultMessage(
                tool_use_id=request.id,
                output=tool_result.output,
                is_error=not tool_result.success,
            )
        )
    return tuple(results)


def _finish(response: ModelResponse, done: int) -> str | None:
    """Câu trả về khi không còn chạy tool. None nghĩa là còn một vòng tool."""

    if response.stop_reason == "end_turn":
        return response.text
    if response.stop_reason == "tool_use" and done >= _MAX_ROUNDS:
        return _CAP
    if response.stop_reason == "tool_use" and response.tool_requests:
        return None
    return _MODEL_ERROR


async def run_turn(
    user_message: str,
    history: Sequence[TextMessage],
    *,
    store: PlanStore,
    api_key: str | None,
    client: ModelClient,
    log: Callable[[str], None] | None = None,
) -> str:
    """Chạy một lượt và trả một chuỗi. Không sửa list lịch sử của người gọi."""

    if api_key is None or api_key == "":
        raise MissingKeyError()
    writer = default_log if log is None else log
    started = _now()
    messages = tuple(history) + (TextMessage(role="user", text=user_message),)
    done: list[tuple[tuple[ToolRequest, ...], tuple[ToolResultMessage, ...]]] = []
    while True:
        remaining = _remaining(started)
        if remaining <= 0:
            return _MODEL_ERROR
        request = ModelRequest(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            rounds=tuple(done),
        )
        call_started = _now()
        try:
            response = await client.complete(request, api_key=api_key, timeout=remaining)
        except Exception as error:
            _model_log(
                writer,
                model=client.model,
                stop_reason=None,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms(call_started, _now()),
                error_type=_error_type(error),
            )
            return _MODEL_ERROR
        _model_log(
            writer,
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            duration_ms=duration_ms(call_started, _now()),
            error_type=None,
        )
        outcome = _finish(response, len(done))
        if outcome is not None:
            return outcome
        tool_results = await _run_tools(
            response.tool_requests,
            store=store,
            log=writer,
            started=started,
        )
        if isinstance(tool_results, str):
            return tool_results
        done.append((response.tool_requests, tool_results))
