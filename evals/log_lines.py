"""Một chỗ đọc dòng log JSON cho eval."""

import json
from collections.abc import Sequence


def parse_log_rows(lines: Sequence[str]) -> list[dict[str, object]]:
    """Parse từng dòng thành object. Bỏ dòng không phải object."""

    found: list[dict[str, object]] = []
    for line in lines:
        item = json.loads(line)
        if isinstance(item, dict):
            found.append(item)
    return found
