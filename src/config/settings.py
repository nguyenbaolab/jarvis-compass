"""Load env vars cho jarvis-compass. Không hardcode giá trị thật."""

import os


def _get_str(key: str, default: str) -> str:
    """Đọc biến môi trường dạng string."""
    return os.getenv(key, default)


ANTHROPIC_API_KEY: str = _get_str("ANTHROPIC_API_KEY", "")
SUPABASE_URL: str = _get_str("SUPABASE_URL", "")
SUPABASE_KEY: str = _get_str("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN: str = _get_str("TELEGRAM_BOT_TOKEN", "")
