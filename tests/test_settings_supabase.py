"""Cấu hình Supabase lấy từ nguồn người gọi, không đọc os.getenv."""

import pytest

from config.settings import SettingsError, require_supabase


def test_empty_dict_ignores_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dict trống vẫn lỗi khi tiến trình đang có sentinel."""

    monkeypatch.setenv("SUPABASE_URL", "sentinel-url")
    monkeypatch.setenv("SUPABASE_KEY", "sentinel-key")
    monkeypatch.setenv("JARVIS_TEST_SUPABASE_URL", "sentinel-test-url")
    monkeypatch.setenv("JARVIS_TEST_SUPABASE_KEY", "sentinel-test-key")
    with pytest.raises(SettingsError) as caught:
        require_supabase({})
    message = str(caught.value)
    assert message == "Thiếu SUPABASE_URL và SUPABASE_KEY."
    assert "sentinel-url" not in message
    assert "sentinel-key" not in message
    assert "sentinel-test-url" not in message
    assert "sentinel-test-key" not in message


def test_dict_and_attribute_object() -> None:
    """Dict và object attribute đều đọc được SUPABASE_URL và SUPABASE_KEY."""

    url = "http://127.0.0.1:54321"
    key = "local-test-key"
    assert require_supabase({"SUPABASE_URL": url, "SUPABASE_KEY": key}) == (url, key)

    class Source:
        SUPABASE_URL = url
        SUPABASE_KEY = key

    assert require_supabase(Source()) == (url, key)


def test_missing_url() -> None:
    with pytest.raises(SettingsError) as caught:
        require_supabase({"SUPABASE_KEY": "present-key"})
    message = str(caught.value)
    assert message == "Thiếu SUPABASE_URL."
    assert "present-key" not in message


def test_missing_key() -> None:
    with pytest.raises(SettingsError) as caught:
        require_supabase({"SUPABASE_URL": "present-url"})
    message = str(caught.value)
    assert message == "Thiếu SUPABASE_KEY."
    assert "present-url" not in message


def test_empty_string_and_non_str() -> None:
    cases = [
        ({"SUPABASE_URL": "", "SUPABASE_KEY": ""}, "Thiếu SUPABASE_URL và SUPABASE_KEY."),
        ({"SUPABASE_URL": None, "SUPABASE_KEY": None}, "Thiếu SUPABASE_URL và SUPABASE_KEY."),
        ({"SUPABASE_URL": 1, "SUPABASE_KEY": 2}, "Thiếu SUPABASE_URL và SUPABASE_KEY."),
        ({"SUPABASE_URL": "", "SUPABASE_KEY": "present-key"}, "Thiếu SUPABASE_URL."),
        ({"SUPABASE_URL": None, "SUPABASE_KEY": "present-key"}, "Thiếu SUPABASE_URL."),
        ({"SUPABASE_URL": "present-url", "SUPABASE_KEY": ""}, "Thiếu SUPABASE_KEY."),
        ({"SUPABASE_URL": "present-url", "SUPABASE_KEY": None}, "Thiếu SUPABASE_KEY."),
    ]
    for source, expected in cases:
        with pytest.raises(SettingsError) as caught:
            require_supabase(source)
        message = str(caught.value)
        assert message == expected
        assert "present-url" not in message
        assert "present-key" not in message


def test_whitespace_is_present() -> None:
    """Chuỗi chỉ khoảng trắng vẫn là có giá trị, không strip."""

    assert require_supabase({"SUPABASE_URL": " ", "SUPABASE_KEY": "\t"}) == (" ", "\t")
