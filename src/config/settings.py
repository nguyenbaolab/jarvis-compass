"""Load env vars cho jarvis-compass. Không hardcode giá trị thật."""

import os
from collections.abc import Mapping


class SettingsError(Exception):
    """Thiếu địa chỉ kho hoặc khóa do nơi gọi truyền vào."""


def _read_setting(source: object, name: str) -> object:
    """Mapping thì .get. Nguồn khác thì getattr. Không đọc os.getenv."""

    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _present(value: object) -> bool:
    """Có giá trị khi là str khác rỗng. Không strip."""

    return isinstance(value, str) and value != ""


def require_supabase(source: object) -> tuple[str, str]:
    """Đọc SUPABASE_URL và SUPABASE_KEY từ nguồn người gọi. Thiếu thì lỗi trước mạng."""

    url = _read_setting(source, "SUPABASE_URL")
    key = _read_setting(source, "SUPABASE_KEY")
    url_ok = _present(url)
    key_ok = _present(key)
    if not url_ok and not key_ok:
        raise SettingsError("Thiếu SUPABASE_URL và SUPABASE_KEY.")
    if not url_ok:
        raise SettingsError("Thiếu SUPABASE_URL.")
    if not key_ok:
        raise SettingsError("Thiếu SUPABASE_KEY.")
    return str(url), str(key)


def _get_str(key: str, default: str) -> str:
    """Đọc biến môi trường dạng string."""
    return os.getenv(key, default)


ANTHROPIC_API_KEY: str = _get_str("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = _get_str("TELEGRAM_BOT_TOKEN", "")
