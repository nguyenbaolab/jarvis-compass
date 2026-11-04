"""Chia câu gửi theo đơn vị UTF-16, không cắt giữa một code point."""

from core.telegram_channel import split_utf16


def _units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def test_exactly_4096_units_is_one_part() -> None:
    text = "a" * 4096
    parts = split_utf16(text)
    assert parts == (text,)
    assert _units(parts[0]) == 4096
    assert all(part != "" for part in parts)


def test_2049_non_bmp_emoji_is_two_parts() -> None:
    emoji = "\U0001f600"
    text = emoji * 2049
    parts = split_utf16(text)
    assert len(parts) == 2
    assert "".join(parts) == text
    assert all(part != "" for part in parts)
    assert all(_units(part) <= 4096 for part in parts)
    assert parts[0] == emoji * 2048
    assert parts[1] == emoji


def test_emoji_straddling_boundary_moves_to_next_part() -> None:
    emoji = "\U0001f600"
    text = "a" * 4095 + emoji
    assert split_utf16(text) == ("a" * 4095, emoji)
