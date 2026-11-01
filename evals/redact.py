"""Thay giá trị khóa không rỗng trong câu trả lời và chuỗi dòng log."""

import json

_HIDDEN = "đã giấu khóa"


def _hide(value: object, key: str) -> object:
    if isinstance(value, str):
        return value.replace(key, _HIDDEN)
    if isinstance(value, list):
        return [_hide(item, key) for item in value]
    if isinstance(value, dict):
        return {name: _hide(item, key) for name, item in value.items()}
    return value


def _hide_line(line: str, key: str) -> str:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return line.replace(key, _HIDDEN)
    return json.dumps(_hide(payload, key), ensure_ascii=False)


def redact(reply: str, lines: tuple[str, ...], key: str) -> tuple[str, tuple[str, ...]]:
    """Khóa rỗng hoặc chỉ khoảng trắng giữ nguyên. Giấu trong giá trị chuỗi, không đổi khóa JSON."""

    if key.strip() == "":
        return reply, tuple(lines)
    return reply.replace(key, _HIDDEN), tuple(_hide_line(line, key) for line in lines)
