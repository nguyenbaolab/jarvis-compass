"""Spike tạm: Haiku gọi create_plan rồi trả lời. Không đưa khóa ra response."""

import hmac
import time
import uuid
from typing import Any

import anthropic
from anthropic.types import Message
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from core.plans import Plan, Subtask
from tools.base import ToolError
from tools.plan_tools import create_plan

router = APIRouter()

_MODEL = "claude-haiku-5-5"
_MAX_TOKENS = 2048
_SYSTEM = (
    "Bạn là trợ lý lập kế hoạch. "
    "Khi người dùng muốn lập kế hoạch, hãy gọi create_plan."
)
_ERROR_LIMIT = 300

# store là tham số keyword-only, route tự truyền, không đưa vào schema.
_CREATE_PLAN_TOOL: dict[str, Any] = {
    "name": "create_plan",
    "description": "Lưu một kế hoạch từ mục tiêu và danh sách việc con.",
    "input_schema": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "Mục tiêu của kế hoạch.",
            },
            "subtasks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tiêu đề từng việc con, theo thứ tự.",
            },
        },
        "required": ["goal"],
    },
}


class MemoryPlanStore:
    """PlanStore trong dict của đúng instance này. created_order bắt đầu ở 1."""

    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._next_order = 1

    def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        """Gán id và created_order. Giữ nguyên goal và thứ tự việc con."""

        plan = Plan(
            id=str(uuid.uuid4()),
            goal=goal,
            subtasks=subtasks,
            created_order=self._next_order,
        )
        self._next_order += 1
        self._plans[plan.id] = plan
        return plan

    def list_newest_first(self) -> tuple[Plan, ...]:
        """created_order lớn hơn đứng trước."""

        return tuple(
            sorted(self._plans.values(), key=lambda plan: plan.created_order, reverse=True)
        )

    def get(self, plan_id: str) -> Plan | None:
        """Trả kế hoạch có đúng id, hoặc None."""

        return self._plans.get(plan_id)

    def replace(self, plan: Plan) -> None:
        """Thay kế hoạch cùng id. Không thêm mới khi id chưa có."""

        if plan.id in self._plans:
            self._plans[plan.id] = plan


def _elapsed_ms(started: float) -> int:
    """Đổi khoảng perf_counter sang mili giây, làm tròn."""

    return round((time.perf_counter() - started) * 1000)


def _redact(message: str, secret: str) -> str:
    """Xóa giá trị khóa khỏi thông điệp, rồi cắt còn 300 ký tự."""

    cleaned = message.replace(secret, "[redacted]") if secret else message
    return cleaned[:_ERROR_LIMIT]


def _spike_guard(request: Request) -> object | Response:
    """Kiểm SPIKE_TOKEN theo route /spike/db. Thiếu env hoặc token thì 503, sai header thì 401."""

    env = request.scope.get("env")
    if env is None:
        return Response(status_code=503)

    token = getattr(env, "SPIKE_TOKEN", None)
    if not isinstance(token, str) or token == "":
        return Response(status_code=503)

    presented = request.headers.get("X-Spike-Token")
    if not isinstance(presented, str):
        return Response(status_code=401)
    try:
        token_ok = hmac.compare_digest(presented, token)
    except Exception:
        token_ok = False
    if not token_ok:
        return Response(status_code=401)
    return env


def _api_key(env: object) -> str | JSONResponse:
    """Đọc ANTHROPIC_API_KEY từ env của request. Thiếu thì 503 kèm tên biến."""

    key = getattr(env, "ANTHROPIC_API_KEY", None)
    if not isinstance(key, str) or key == "":
        return JSONResponse(status_code=503, content={"missing": ["ANTHROPIC_API_KEY"]})
    return key


def _anthropic_error(
    exc: Exception,
    stage: str,
    secret: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Trả mã HTTP và loại lỗi. Không trả header hay giá trị khóa."""

    if isinstance(exc, anthropic.APIStatusError):
        body: dict[str, Any] = {
            "status_code": exc.status_code,
            "type": type(exc).__name__,
            "stage": stage,
            "message": _redact(str(exc), secret),
        }
        if exc.type is not None:
            body["api_type"] = exc.type
        http_status = exc.status_code
    else:
        body = {
            "status_code": None,
            "type": type(exc).__name__,
            "stage": stage,
            "message": _redact(str(exc), secret),
        }
        http_status = 502
    content: dict[str, Any] = {"error": body}
    if extra:
        content.update(extra)
    return JSONResponse(status_code=http_status, content=content)


def _call_record(message: Message, duration_ms: int) -> dict[str, Any]:
    """stop_reason và usage của một lần Messages API."""

    return {
        "stop_reason": message.stop_reason,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
        "duration_ms": duration_ms,
    }


def _message_text(message: Message) -> str:
    """Nối các khối type text. Không lấy thinking."""

    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", "")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _run_create_plan(raw_input: object, store: MemoryPlanStore) -> tuple[str, bool]:
    """Gọi create_plan thật. ToolError và mọi lỗi Python thành tool_result lỗi."""

    if not isinstance(raw_input, dict):
        return "Input của create_plan không phải object.", True
    goal: Any = raw_input.get("goal")
    subtasks: Any = raw_input.get("subtasks") if "subtasks" in raw_input else None
    try:
        result = create_plan(goal, subtasks, store=store)
    except ToolError as error:
        return str(error), True
    except Exception as error:
        return type(error).__name__ + ": " + str(error), True
    return result.output, False


def _create(client: anthropic.Anthropic, messages: list[dict[str, Any]]) -> tuple[Message, int]:
    """Một lần messages.create. Cùng model, max_tokens, system và tools."""

    started = time.perf_counter()
    message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM,
        tools=[_CREATE_PLAN_TOOL],
        messages=messages,
    )
    return message, _elapsed_ms(started)


@router.post("/spike/haiku")
async def spike_haiku(request: Request) -> Response:
    """Gửi một câu cho Haiku, chạy create_plan nếu được gọi, rồi trả lời cuối."""

    started = time.perf_counter()
    guard = _spike_guard(request)
    if isinstance(guard, Response):
        return guard
    env = guard

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"type": "invalid_json"}})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": {"type": "invalid_body"}})
    text = payload.get("text")
    if not isinstance(text, str):
        return JSONResponse(status_code=400, content={"error": {"type": "invalid_text"}})

    key = _api_key(env)
    if isinstance(key, JSONResponse):
        return key

    try:
        client = anthropic.Anthropic(api_key=key)
    except Exception as exc:
        return _anthropic_error(exc, "client", key)

    try:
        try:
            first, first_ms = _create(
                client, [{"role": "user", "content": text}]
            )
        except Exception as exc:
            return _anthropic_error(exc, "call_1", key)

        calls = [_call_record(first, first_ms)]
        tool_blocks = [block for block in first.content if getattr(block, "type", None) == "tool_use"]
        if first.stop_reason != "tool_use" or not tool_blocks:
            return JSONResponse(
                content={
                    "total_ms": _elapsed_ms(started),
                    "calls": calls,
                    "tool_use": None,
                    "note": "không có tool_use",
                    "text": _message_text(first),
                }
            )

        store = MemoryPlanStore()
        tool_results: list[dict[str, Any]] = []
        reported: list[dict[str, Any]] = []
        for block in tool_blocks:
            raw_input = getattr(block, "input", None)
            if getattr(block, "name", None) == "create_plan":
                result_text, is_error = _run_create_plan(raw_input, store)
            else:
                result_text, is_error = "Spike chỉ chạy create_plan.", True
            result_block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": getattr(block, "id", ""),
                "content": result_text,
            }
            if is_error:
                result_block["is_error"] = True
            tool_results.append(result_block)
            reported.append(
                {
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": raw_input,
                    "result": result_text,
                    "is_error": is_error,
                }
            )

        # Content lần 1 nguyên vẹn, kể cả thinking nếu có. SDK tự serialize.
        follow_up: list[dict[str, Any]] = [
            {"role": "user", "content": text},
            {"role": "assistant", "content": first.content},
            {"role": "user", "content": tool_results},
        ]
        try:
            second, second_ms = _create(client, follow_up)
        except Exception as exc:
            return _anthropic_error(
                exc,
                "call_2",
                key,
                extra={"calls": calls, "tool_use": reported},
            )
        calls.append(_call_record(second, second_ms))
        return JSONResponse(
            content={
                "total_ms": _elapsed_ms(started),
                "calls": calls,
                "tool_use": reported,
                "text": _message_text(second),
            }
        )
    finally:
        try:
            client.close()
        except Exception:
            pass
