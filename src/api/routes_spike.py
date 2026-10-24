"""Spike tạm: webhook Telegram chạy vòng Haiku rồi trả lời. Không đưa token hay secret ra response."""

import hmac
import json
import time
import uuid
from typing import Any

import anthropic
import httpx
from anthropic.types import Message
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from core.plans import Plan, Subtask
from tools.base import ToolError
from tools.plan_tools import create_plan

router = APIRouter()

_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_TIMEOUT_SECONDS = 10.0
_TEXT_LIMIT = 4000
_EMPTY_REPLY = "(Haiku không trả lời chữ)"
_MODEL = "claude-haiku-5-5"
_MAX_TOKENS = 2048
_SYSTEM = (
    "Bạn là trợ lý lập kế hoạch. "
    "Khi người dùng muốn lập kế hoạch, hãy gọi create_plan."
)

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


def _guard(request: Request) -> tuple[str, str] | Response:
    """Thiếu env hoặc một secret thì 503. Header thiếu hoặc sai thì 401."""

    env = request.scope.get("env")
    if env is None:
        return Response(status_code=503)

    webhook_secret = getattr(env, "TELEGRAM_WEBHOOK_SECRET", None)
    bot_token = getattr(env, "TELEGRAM_BOT_TOKEN", None)
    api_key = getattr(env, "ANTHROPIC_API_KEY", None)
    if not isinstance(webhook_secret, str) or webhook_secret == "":
        return Response(status_code=503)
    if not isinstance(bot_token, str) or bot_token == "":
        return Response(status_code=503)
    if not isinstance(api_key, str) or api_key == "":
        return Response(status_code=503)

    presented = request.headers.get(_SECRET_HEADER)
    if not isinstance(presented, str):
        return Response(status_code=401)
    try:
        secret_ok = hmac.compare_digest(presented, webhook_secret)
    except Exception:
        secret_ok = False
    if not secret_ok:
        return Response(status_code=401)
    return bot_token, api_key


def _with_update_id(body: dict[str, Any], payload: object) -> dict[str, Any]:
    """Gắn update_id khi payload là object và có khóa đó."""

    if isinstance(payload, dict) and "update_id" in payload:
        body["update_id"] = payload["update_id"]
    return body


def _ignored(payload: object, reason: str) -> JSONResponse:
    """200 và không gọi sendMessage. Telegram gửi lại update khi nhận mã khác 2xx."""

    content = _with_update_id({"action": "ignored", "reason": reason}, payload)
    return JSONResponse(status_code=200, content=content)


def _chat_id(message: dict[str, Any]) -> int | None:
    """Lấy message.chat.id khi là int. bool không được tính là id."""

    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    if isinstance(chat_id, bool) or not isinstance(chat_id, int):
        return None
    return chat_id


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
    """Gọi create_plan thật. ToolError giữ câu tiếng Việt. Lỗi Python khác chỉ là tên lớp."""

    if not isinstance(raw_input, dict):
        return "Input của create_plan không phải object.", True
    goal: Any = raw_input.get("goal")
    subtasks: Any = raw_input.get("subtasks") if "subtasks" in raw_input else None
    try:
        result = create_plan(goal, subtasks, store=store)
    except ToolError as error:
        return str(error), True
    except Exception as error:
        return type(error).__name__, True
    return result.output, False


def _create(client: anthropic.Anthropic, messages: list[dict[str, Any]]) -> Message:
    """Một lần messages.create. Cùng model, max_tokens, system và tools."""

    return client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM,
        tools=[_CREATE_PLAN_TOOL],
        messages=messages,
    )


def _haiku_failure(exc: Exception) -> tuple[str, str, int | None]:
    """Tên lớp và mã HTTP. Không đọc chuỗi của exception."""

    name = type(exc).__name__
    status: int | None = None
    if isinstance(exc, anthropic.APIStatusError) and type(exc.status_code) is int:
        status = exc.status_code
    if status is None:
        return f"Lỗi khi gọi Haiku: {name}", name, None
    return f"Lỗi khi gọi Haiku: {name} {status}", name, status


def _empty_trace() -> dict[str, Any]:
    """Số đo Haiku trước khi có lần gọi nào."""

    return {
        "haiku_calls": [],
        "tool_use": False,
        "tool_uses": [],
        "create_plan_is_error": None,
        "haiku_error_type": None,
        "haiku_error_status": None,
    }


def _record_call(trace: dict[str, Any], message: Message | None, started: float) -> None:
    """Ghi mili giây và usage. Lần gọi lỗi, hoặc usage không đọc được, để null."""

    record: dict[str, Any] = {
        "ms": _elapsed_ms(started),
        "input_tokens": None,
        "output_tokens": None,
    }
    if message is not None:
        try:
            record["input_tokens"] = message.usage.input_tokens
            record["output_tokens"] = message.usage.output_tokens
        except Exception:
            pass
    trace["haiku_calls"].append(record)


def _note_failure(trace: dict[str, Any], exc: Exception) -> str:
    """Ghi lỗi Haiku vào trace và trả câu sẽ gửi Telegram."""

    reply, name, status = _haiku_failure(exc)
    trace["haiku_error_type"] = name
    trace["haiku_error_status"] = status
    return reply


def _mark_create_plan(trace: dict[str, Any], is_error: bool) -> None:
    """True nếu bất kỳ lần create_plan nào trả is_error."""

    previous = trace["create_plan_is_error"]
    if previous is None:
        trace["create_plan_is_error"] = is_error
    elif is_error:
        trace["create_plan_is_error"] = True


def _tool_results(
    blocks: list[Any],
    store: MemoryPlanStore,
    trace: dict[str, Any],
) -> list[dict[str, Any]]:
    """Chạy từng tool_use. create_plan thật; tool khác là lỗi."""

    results: list[dict[str, Any]] = []
    for block in blocks:
        raw_input = getattr(block, "input", None)
        if getattr(block, "name", None) == "create_plan":
            result_text, is_error = _run_create_plan(raw_input, store)
            _mark_create_plan(trace, is_error)
        else:
            result_text, is_error = "Spike chỉ chạy create_plan.", True
        result_block: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": getattr(block, "id", ""),
            "content": result_text,
        }
        if is_error:
            result_block["is_error"] = True
        results.append(result_block)
        trace["tool_uses"].append(
            {
                "name": getattr(block, "name", None),
                "input": raw_input,
                "is_error": is_error,
            }
        )
    return results


def _converse(
    client: anthropic.Anthropic,
    text: str,
    store: MemoryPlanStore,
    trace: dict[str, Any],
) -> str:
    """Lần 1, rồi lần 2 nếu có tool_use. Content lần 1 gửi lại nguyên."""

    started = time.perf_counter()
    try:
        first = _create(client, [{"role": "user", "content": text}])
    except Exception as exc:
        _record_call(trace, None, started)
        return _note_failure(trace, exc)
    _record_call(trace, first, started)

    tool_blocks = [block for block in first.content if getattr(block, "type", None) == "tool_use"]
    if first.stop_reason != "tool_use" or not tool_blocks:
        return _message_text(first)

    trace["tool_use"] = True
    follow_up: list[dict[str, Any]] = [
        {"role": "user", "content": text},
        {"role": "assistant", "content": first.content},
        {"role": "user", "content": _tool_results(tool_blocks, store, trace)},
    ]
    started = time.perf_counter()
    try:
        second = _create(client, follow_up)
    except Exception as exc:
        _record_call(trace, None, started)
        return _note_failure(trace, exc)
    _record_call(trace, second, started)
    return _message_text(second)


def _run_haiku(api_key: str, text: str, store: MemoryPlanStore) -> tuple[str, dict[str, Any]]:
    """Store của request này. Mọi lỗi Anthropic thành câu chữ, không thoát ra ngoài."""

    trace = _empty_trace()
    client: anthropic.Anthropic | None = None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        return _converse(client, text, store, trace), trace
    except Exception as exc:
        return _note_failure(trace, exc), trace
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _outgoing_text(text: str) -> str:
    """Text rỗng đổi thành câu báo. Cắt còn tối đa 4000 ký tự."""

    if text == "":
        text = _EMPTY_REPLY
    return text[:_TEXT_LIMIT]


async def _send_message(bot_token: str, chat_id: int, text: str) -> dict[str, Any]:
    """POST sendMessage. Chỉ giữ mã HTTP, ok, mili giây, hoặc tên lớp lỗi."""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text},
            )
    except Exception as exc:
        return {
            "send_status": None,
            "send_ok": None,
            "send_error_type": type(exc).__name__,
            "send_ms": _elapsed_ms(started),
        }

    send_ok: Any = None
    try:
        parsed = response.json()
    except Exception:
        parsed = None
    if isinstance(parsed, dict) and "ok" in parsed:
        send_ok = parsed["ok"]
    return {
        "send_status": response.status_code,
        "send_ok": send_ok,
        "send_error_type": None,
        "send_ms": _elapsed_ms(started),
    }


def _public_send(sent: dict[str, Any]) -> dict[str, Any]:
    """Body HTTP không có chữ của người dùng hay của Haiku."""

    body: dict[str, Any] = {"action": "replied", "send_ms": sent["send_ms"]}
    if sent["send_error_type"] is not None:
        body["reason"] = sent["send_error_type"]
        return body
    body["send_status"] = sent["send_status"]
    body["send_ok"] = sent["send_ok"]
    return body


def _print_log(
    payload: dict[str, Any],
    trace: dict[str, Any],
    sent: dict[str, Any],
    total_ms: int,
) -> None:
    """Đúng một dòng JSON. Không có text người dùng, text Haiku, token, khóa hay secret."""

    line = json.dumps(
        {
            "update_id": payload.get("update_id"),
            "haiku_calls": trace["haiku_calls"],
            "tool_use": trace["tool_use"],
            "tool_uses": trace["tool_uses"],
            "create_plan_is_error": trace["create_plan_is_error"],
            "haiku_error_type": trace["haiku_error_type"],
            "haiku_error_status": trace["haiku_error_status"],
            "send_status": sent["send_status"],
            "send_ok": sent["send_ok"],
            "send_error_type": sent["send_error_type"],
            "send_ms": sent["send_ms"],
            "total_ms": total_ms,
        },
        ensure_ascii=False,
    )
    print(line, flush=True)


@router.post("/spike/telegram")
async def spike_telegram(request: Request) -> Response:
    """Secret đúng thì luôn 200. Có message.text thì Haiku trả lời về đúng chat.id."""

    started = time.perf_counter()
    guarded = _guard(request)
    if isinstance(guarded, Response):
        return guarded
    bot_token, api_key = guarded

    try:
        payload = await request.json()
    except Exception:
        return _ignored(None, "json không đọc được")
    if not isinstance(payload, dict):
        return _ignored(None, "body không phải object")

    message = payload.get("message")
    if not isinstance(message, dict):
        return _ignored(payload, "không có message")
    text = message.get("text")
    if not isinstance(text, str):
        return _ignored(payload, "không có text")
    chat_id = _chat_id(message)
    if chat_id is None:
        return _ignored(payload, "không có chat.id")

    trace = _empty_trace()
    try:
        reply, trace = _run_haiku(api_key, text, MemoryPlanStore())
    except Exception as exc:
        reply = _note_failure(trace, exc)
    try:
        sent = await _send_message(bot_token, chat_id, _outgoing_text(reply))
    except Exception as exc:
        sent = {
            "send_status": None,
            "send_ok": None,
            "send_error_type": type(exc).__name__,
            "send_ms": 0,
        }
    try:
        _print_log(payload, trace, sent, _elapsed_ms(started))
    except Exception:
        pass
    return JSONResponse(status_code=200, content=_with_update_id(_public_send(sent), payload))
