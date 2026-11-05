"""Load env vars cho jarvis-compass. Không hardcode giá trị thật."""

from collections.abc import Mapping


class SettingsError(Exception):
    """Thiếu địa chỉ kho hoặc khóa do nơi gọi truyền vào."""


def _read_setting(source: object, name: str) -> object:
    """Mapping thì .get. Nguồn khác thì getattr. Không đọc biến môi trường của tiến trình."""

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


def _require(source: object, name: str) -> str:
    value = _read_setting(source, name)
    if not _present(value):
        raise SettingsError(f"Thiếu {name}.")
    return str(value)


def require_telegram_webhook_secret(source: object) -> str:
    """Đọc TELEGRAM_WEBHOOK_SECRET. Thiếu hoặc rỗng thì lỗi. Không strip."""

    return _require(source, "TELEGRAM_WEBHOOK_SECRET")


def require_telegram_bot_token(source: object) -> str:
    """Đọc TELEGRAM_BOT_TOKEN. Thiếu hoặc rỗng thì lỗi. Không strip."""

    return _require(source, "TELEGRAM_BOT_TOKEN")


def require_telegram_owner_id(source: object) -> str:
    """Đọc TELEGRAM_OWNER_ID. Thiếu hoặc rỗng thì lỗi. Không strip."""

    return _require(source, "TELEGRAM_OWNER_ID")


def require_anthropic_api_key(source: object) -> str:
    """Đọc ANTHROPIC_API_KEY. Thiếu hoặc rỗng thì lỗi. Không strip."""

    return _require(source, "ANTHROPIC_API_KEY")


def owner_id_matches(configured: str, user_id: object) -> bool:
    """Khớp khi user_id là int, không phải bool, và str(user_id) đúng bằng chuỗi cấu hình."""

    if isinstance(user_id, bool) or not isinstance(user_id, int):
        return False
    return str(user_id) == configured
