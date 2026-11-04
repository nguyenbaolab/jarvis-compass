"""Bốn hàm đọc cấu hình Telegram và luật so mã chủ bot."""

import pytest

from config.settings import (
    SettingsError,
    owner_id_matches,
    require_anthropic_api_key,
    require_telegram_bot_token,
    require_telegram_owner_id,
    require_telegram_webhook_secret,
)


def test_require_telegram_settings_missing_raises() -> None:
    readers = (
        (require_telegram_webhook_secret, "TELEGRAM_WEBHOOK_SECRET", "Thiếu TELEGRAM_WEBHOOK_SECRET."),
        (require_telegram_bot_token, "TELEGRAM_BOT_TOKEN", "Thiếu TELEGRAM_BOT_TOKEN."),
        (require_telegram_owner_id, "TELEGRAM_OWNER_ID", "Thiếu TELEGRAM_OWNER_ID."),
        (require_anthropic_api_key, "ANTHROPIC_API_KEY", "Thiếu ANTHROPIC_API_KEY."),
    )
    for reader, name, message in readers:
        with pytest.raises(SettingsError) as missing:
            reader({})
        assert str(missing.value) == message
        with pytest.raises(SettingsError) as empty:
            reader({name: ""})
        assert str(empty.value) == message
        assert reader({name: "  "}) == "  "
        assert reader({name: "abc"}) == "abc"


def test_owner_id_match_rules() -> None:
    assert owner_id_matches("123", 123) is True
    assert owner_id_matches(" 123", 123) is False
    assert owner_id_matches("123", True) is False
    assert owner_id_matches("1", True) is False
    assert owner_id_matches("123", "123") is False
