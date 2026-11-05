"""Ghi một dòng JSON dùng chung. Chỉ thư viện chuẩn."""

import json
import re
from collections.abc import Callable

_ERROR_CODE = re.compile(r"^[A-Za-z0-9_]{1,16}$")


def error_code_of(error: BaseException) -> str | None:
    """Đọc thuộc tính `code` theo duck typing vì api/ không được import db.

    Trong thực tế chỉ postgrest APIError có thuộc tính này trong các exception tới nhánh kho.
    """

    code = getattr(error, "code", None)
    if type(code) is int:
        return str(code)
    if type(code) is str and _ERROR_CODE.fullmatch(code):
        return code
    return None


def default_log(line: str) -> None:
    """In một dòng khi người gọi không đưa hàm ghi."""

    print(line, flush=True)


def duration_ms(started: float, ended: float) -> int:
    """Đổi hiệu hai mốc ra mili giây. Hiệu không dương thì bằng 0."""

    elapsed = ended - started
    if elapsed <= 0:
        return 0
    return int(elapsed * 1000)


def write_json_line(log: Callable[[str], None], payload: dict[str, object]) -> None:
    """Ghi một dòng JSON. Exception của dumps hoặc hàm log bị nuốt. CancelledError đi tiếp."""

    try:
        line = json.dumps(payload, ensure_ascii=False)
        log(line)
    except Exception:
        return
