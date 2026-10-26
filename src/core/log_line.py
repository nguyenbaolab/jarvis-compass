"""Ghi một dòng JSON dùng chung. Chỉ thư viện chuẩn."""

import json
from collections.abc import Callable


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
