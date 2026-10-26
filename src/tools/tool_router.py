"""Điều phối sáu tool: kiểm đầu vào, gọi tool, ghi một dòng nhật ký."""

import json
import time
from collections.abc import Awaitable, Callable

from core.log_line import default_log, duration_ms, write_json_line
from core.plans import PlanDomainError, PlanStore
from tools.base import ToolError, ToolResult
from tools.plan_tools import (
    add_subtask,
    create_plan,
    get_plan_detail,
    get_plans,
    set_subtask_note,
    update_subtask,
)
from tools.tool_definitions import DEFINITIONS_VERSION, TOOL_DEFINITIONS

_UNKNOWN = "Không có tool với tên này."
_NOT_OBJECT = "Đầu vào phải là một object."
_UNEXPECTED = "Không thực hiện được yêu cầu này."

_LOG_KEYS = (
    "tool",
    "input",
    "ok",
    "error_type",
    "duration_ms",
    "definitions_version",
    "detail",
)

_Handler = Callable[[dict[str, object], PlanStore], Awaitable[ToolResult]]


def _now() -> float:
    """Mốc monotonic của lần gọi. Tách khỏi đồng hồ mà asyncio cũng đọc."""

    return time.monotonic()


def _failure(
    output: str,
    error_type: str,
    detail: str | None = None,
) -> tuple[ToolResult, str, str | None]:
    """Một kết quả lỗi và nhãn ghi vào dòng nhật ký."""

    return ToolResult(success=False, output=output), error_type, detail


def _wrong_type(name: str) -> str:
    """Câu sai kiểu của cả trường."""

    return f"Trường {name} sai kiểu."


def _wrong_item(name: str) -> str:
    """Câu sai kiểu của một phần tử mảng."""

    return f"Một phần tử của trường {name} sai kiểu."


async def _create(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    """create_plan. Bỏ subtasks khi khóa không có."""

    if "subtasks" in tool_input:
        return await create_plan(tool_input["goal"], subtasks=tool_input["subtasks"], store=store)
    return await create_plan(tool_input["goal"], store=store)


async def _list(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    """get_plans. Bỏ keyword khi khóa không có."""

    if "keyword" in tool_input:
        return await get_plans(keyword=tool_input["keyword"], store=store)
    return await get_plans(store=store)


async def _detail(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    return await get_plan_detail(tool_input["plan_id"], store=store)


async def _update(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    return await update_subtask(
        tool_input["plan_id"],
        tool_input["subtask_id"],
        tool_input["status"],
        store=store,
    )


async def _add(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    return await add_subtask(tool_input["plan_id"], tool_input["title"], store=store)


async def _note(tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    return await set_subtask_note(
        tool_input["plan_id"],
        tool_input["subtask_id"],
        tool_input["note"],
        store=store,
    )


_DISPATCH: dict[str, _Handler] = {
    "create_plan": _create,
    "get_plans": _list,
    "get_plan_detail": _detail,
    "update_subtask": _update,
    "add_subtask": _add,
    "set_subtask_note": _note,
}


def _type_error(name: str, value: object, spec: dict[str, object]) -> str | None:
    """Câu sai kiểu của một trường, hoặc None khi đúng kiểu. Schema lạ thì ném."""

    kind = spec["type"]
    if kind == "string":
        if isinstance(value, str):
            return None
        return _wrong_type(name)
    if kind == "array":
        if not isinstance(value, list):
            return _wrong_type(name)
        for item in value:
            if not isinstance(item, str):
                return _wrong_item(name)
        return None
    raise TypeError("Kiểu trong catalog không được hỗ trợ.")


def _invalid_input(name: str, tool_input: dict[str, object]) -> str | None:
    """Câu đầu vào sai đầu tiên, hoặc None khi object hợp schema. Catalog hỏng thì ném."""

    schema = TOOL_DEFINITIONS[name]["input_schema"]
    if not isinstance(schema, dict):
        raise TypeError("Schema đầu vào không phải object.")
    properties = schema["properties"]
    required = schema["required"]
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise TypeError("Schema đầu vào thiếu properties hoặc required.")
    if schema.get("additionalProperties") is False:
        for key in tool_input:
            if key not in properties:
                return f"Đầu vào thừa trường {key}."
    for key in required:
        if not isinstance(key, str):
            raise TypeError("Tên trường bắt buộc không phải chuỗi.")
        if key not in tool_input:
            return f"Đầu vào thiếu trường {key}."
    for key in properties:
        if key not in tool_input:
            continue
        spec = properties[key]
        if not isinstance(spec, dict):
            raise TypeError("Mô tả trường không phải object.")
        message = _type_error(str(key), tool_input[key], spec)
        if message is not None:
            return message
    return None


async def _invoke(name: str, tool_input: dict[str, object], store: PlanStore) -> ToolResult:
    """Gọi hàm trong bảng tên. Bỏ khóa tùy chọn khi object không có."""

    return await _DISPATCH[name](tool_input, store)


def _log_tool(name: object) -> object:
    """Tên chuỗi ghi nguyên. Giá trị khác thành null."""

    if isinstance(name, str):
        return name
    return None


def _log_input(tool_input: object) -> object:
    """Đầu vào nếu dumps được. Mọi Exception, kể cả RecursionError, thành null."""

    try:
        json.dumps(tool_input, ensure_ascii=False)
    except Exception:
        return None
    return tool_input


def _write_log(
    name: object,
    tool_input: object,
    result: ToolResult,
    error_type: str | None,
    detail: str | None,
    started: float,
    log: Callable[[str], None] | None,
) -> None:
    """Một dòng JSON bảy khóa. Hàm ghi ném Exception thì nuốt, vẫn giữ kết quả."""

    payload = {
        "tool": _log_tool(name),
        "input": _log_input(tool_input),
        "ok": result.success,
        "error_type": error_type,
        "duration_ms": duration_ms(started, _now()),
        "definitions_version": DEFINITIONS_VERSION,
        "detail": detail,
    }
    writer = default_log if log is None else log
    write_json_line(writer, {key: payload[key] for key in _LOG_KEYS})


async def _run(
    name: object,
    tool_input: object,
    store: PlanStore,
) -> tuple[ToolResult, str | None, str | None]:
    """Phân loại. BaseException không bị bắt ở đây. Catalog hỏng là unexpected."""

    if not isinstance(name, str) or name not in TOOL_DEFINITIONS:
        return _failure(_UNKNOWN, "unknown_tool")
    if not isinstance(tool_input, dict):
        return _failure(_NOT_OBJECT, "invalid_input")
    try:
        message = _invalid_input(name, tool_input)
    except Exception as error:
        return _failure(_UNEXPECTED, "unexpected", type(error).__name__)
    if message is not None:
        return _failure(message, "invalid_input")
    try:
        result = await _invoke(name, tool_input, store)
    except (ToolError, PlanDomainError) as error:
        return _failure(str(error), "domain")
    except Exception as error:
        return _failure(_UNEXPECTED, "unexpected", type(error).__name__)
    return result, None, None


async def execute_tool(
    name: object,
    tool_input: object,
    *,
    store: PlanStore,
    log: Callable[[str], None] | None = None,
) -> ToolResult:
    """Chạy một tool trên kho được truyền vào và ghi đúng một dòng khi có kết quả."""

    started = _now()
    result, error_type, detail = await _run(name, tool_input, store)
    _write_log(name, tool_input, result, error_type, detail, started, log)
    return result
