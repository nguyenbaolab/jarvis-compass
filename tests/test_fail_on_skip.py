"""Bốn ca của hàm quyết định mã thoát khi có skip."""

import pytest

from tests.conftest import exit_code_for_skips


@pytest.mark.parametrize(
    ("skip_count", "current_code", "expected"),
    [
        (3, 0, 6),
        (0, 0, 0),
        (3, 1, 1),
        (0, 1, 1),
    ],
)
def test_exit_code_for_skips(skip_count: int, current_code: int, expected: int) -> None:
    assert exit_code_for_skips(skip_count, current_code) == expected
