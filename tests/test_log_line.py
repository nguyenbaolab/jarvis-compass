"""Hàm dùng chung cho một dòng JSON."""

import asyncio
import json

import pytest

from core.log_line import duration_ms, write_json_line


def test_duration_ms_negative_is_zero() -> None:
    assert duration_ms(5.0, 4.0) == 0


def test_duration_ms_zero_is_zero() -> None:
    assert duration_ms(1.0, 1.0) == 0


def test_duration_ms_one_and_a_half_milliseconds_is_one() -> None:
    assert duration_ms(0.0, 0.0015) == 1


def test_duration_ms_one_and_a_half_seconds_is_1500() -> None:
    assert duration_ms(0.0, 1.5) == 1500


def test_write_json_line_keeps_one_vietnamese_line() -> None:
    payload: dict[str, object] = {"text": "Tiếng Việt"}
    lines: list[str] = []
    write_json_line(lines.append, payload)
    assert lines == [json.dumps(payload, ensure_ascii=False)]
    assert len(lines) == 1


def test_write_json_line_swallows_log_exception() -> None:
    def fail(line: str) -> None:
        raise RuntimeError(line)

    write_json_line(fail, {"text": "Ổn"})


def test_write_json_line_skips_log_when_payload_not_dumpable() -> None:
    calls: list[str] = []

    def record(line: str) -> None:
        calls.append(line)

    write_json_line(record, {"value": object()})
    assert calls == []


def test_write_json_line_propagates_cancelled_error() -> None:
    def fail(line: str) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        write_json_line(fail, {"text": "Ổn"})
