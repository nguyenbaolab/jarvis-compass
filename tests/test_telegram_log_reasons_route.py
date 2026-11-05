"""Một dòng nhật ký cho mỗi POST /telegram: reject, ignore, và unexpected."""

import json
from datetime import datetime, timezone

import pytest

from tests.test_telegram_route import (
    MemoryPlanStore,
    MemoryTelegramChannel,
    ModelResponse,
    _SECRET,
    _TOKEN,
    _WRONG,
    _Hits,
    _deps,
    _env,
    _message,
    _post,
)

_TEXT = "chu tin khong log"
_REPLY = "cau tra loi khong log"
_LEAK = f"boom {_SECRET}"
_HEADER = {"X-Telegram-Bot-Api-Secret-Token": _SECRET}
_KEYS = {"outcome", "reason", "update_id", "error_type", "error_code"}
_FORBIDDEN = (_SECRET, _WRONG, _TOKEN, _TEXT, _REPLY, _LEAK)


class LeakError(Exception):
    """Exception giả. Thông điệp chứa secret và không được vào nhật ký."""


class _InsertedBomb:
    @property
    def inserted(self) -> bool:
        raise LeakError(_LEAK)


class _BombStore:
    async def claim(self, update_id: int, started_at: object) -> _InsertedBomb:
        del update_id, started_at
        return _InsertedBomb()


def _outcome_lines(logs: list[str]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for line in logs:
        item = json.loads(line)
        if isinstance(item, dict) and "outcome" in item:
            found.append(item)
    return found


def _assert_channel(
    item: dict[str, object],
    outcome: str,
    reason: str,
    update_id: int | None,
    error_type: str | None,
    error_code: str | None = None,
) -> None:
    assert set(item) <= _KEYS
    keys = ["outcome", "reason"]
    if update_id is not None:
        keys.append("update_id")
    if error_type is not None:
        keys.append("error_type")
    if error_code is not None:
        keys.append("error_code")
    assert list(item) == keys
    assert item["outcome"] == outcome
    assert item["reason"] == reason
    if update_id is None:
        assert "update_id" not in item
    else:
        assert item["update_id"] == update_id
    if error_type is None:
        assert "error_type" not in item
    else:
        assert item["error_type"] == error_type
    if error_code is None:
        assert "error_code" not in item
    else:
        assert item["error_code"] == error_code


def _forbid(logs: list[str]) -> None:
    blob = "\n".join(logs)
    for secret in _FORBIDDEN:
        assert secret not in blob


def _send(reason: str, logs: list[str]) -> object:
    hits = _Hits()
    if reason == "secret_not_configured":
        deps = _deps(
            hits,
            env={"TELEGRAM_BOT_TOKEN": _TOKEN, "TELEGRAM_OWNER_ID": "123"},
            logs=logs,
        )
        return _post(deps, _message(update_id=11, text=_TEXT), _HEADER)
    if reason == "secret_header_missing":
        return _post(_deps(hits, logs=logs), _message(update_id=12, text=_TEXT), {})
    if reason == "secret_mismatch":
        return _post(
            _deps(hits, logs=logs),
            _message(update_id=13, text=_TEXT),
            {"X-Telegram-Bot-Api-Secret-Token": _WRONG},
        )
    if reason == "token_not_configured":
        deps = _deps(
            hits,
            env={"TELEGRAM_WEBHOOK_SECRET": _SECRET, "TELEGRAM_OWNER_ID": "123"},
            logs=logs,
        )
        return _post(deps, _message(update_id=14, text=_TEXT), _HEADER)
    if reason == "body_unreadable":
        return _post(_deps(hits, logs=logs), None, _HEADER, raw=b"{")
    if reason == "owner_not_configured":
        deps = _deps(
            hits,
            env={"TELEGRAM_WEBHOOK_SECRET": _SECRET, "TELEGRAM_BOT_TOKEN": _TOKEN},
            logs=logs,
        )
        return _post(deps, _message(update_id=21, text=_TEXT), _HEADER)
    if reason == "not_a_message":
        body = {"update_id": 22, "edited_message": {"text": _TEXT}}
        return _post(_deps(hits, logs=logs), body, _HEADER)
    if reason == "not_private_chat":
        return _post(
            _deps(hits, logs=logs),
            _message(update_id=23, text=_TEXT, chat_type="group"),
            _HEADER,
        )
    if reason == "not_owner":
        return _post(
            _deps(hits, logs=logs),
            _message(update_id=24, text=_TEXT, user_id=999),
            _HEADER,
        )
    if reason == "bad_ids":
        body = {
            "update_id": 25,
            "message": {
                "message_id": 1,
                "text": _TEXT,
                "chat": {"id": "7", "type": "private"},
                "from": {"id": 123},
            },
        }
        return _post(_deps(hits, logs=logs), body, _HEADER)
    if reason == "unexpected":

        async def open_channel() -> tuple[_BombStore, _BombStore]:
            store = _BombStore()
            return store, store

        deps = _deps(hits, open_channel=open_channel, logs=logs)
        return _post(deps, _message(update_id=77, text=_TEXT), _HEADER)
    raise AssertionError(reason)


@pytest.mark.parametrize(
    ("reason", "outcome", "status", "update_id", "error_type"),
    [
        pytest.param("secret_not_configured", "reject", 401, None, None, id="secret_not_configured"),
        pytest.param("secret_header_missing", "reject", 401, None, None, id="secret_header_missing"),
        pytest.param("secret_mismatch", "reject", 401, None, None, id="secret_mismatch"),
        pytest.param("token_not_configured", "reject", 401, None, None, id="token_not_configured"),
        pytest.param("body_unreadable", "ignore", 200, None, None, id="body_unreadable"),
        pytest.param("owner_not_configured", "ignore", 200, 21, None, id="owner_not_configured"),
        pytest.param("not_a_message", "ignore", 200, 22, None, id="not_a_message"),
        pytest.param("not_private_chat", "ignore", 200, 23, None, id="not_private_chat"),
        pytest.param("not_owner", "ignore", 200, 24, None, id="not_owner"),
        pytest.param("bad_ids", "ignore", 200, 25, None, id="bad_ids"),
        pytest.param("unexpected", "defer", 503, 77, "LeakError", id="unexpected"),
    ],
)
def test_route_log_reason(
    reason: str,
    outcome: str,
    status: int,
    update_id: int | None,
    error_type: str | None,
) -> None:
    logs: list[str] = []
    response = _send(reason, logs)
    assert response.status_code == status
    assert response.content == b""
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], outcome, reason, update_id, error_type)
    _forbid(logs)


def test_route_done_logs_replied() -> None:
    store = MemoryTelegramChannel()

    class _Sender:
        async def send_part(self, chat_id: int, text: str) -> None:
            del chat_id, text

    class _Model:
        def __init__(self) -> None:
            self.model = "scripted"

        async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
            del request, api_key, timeout
            return ModelResponse("xong", (), "end_turn", 1, 1, "scripted")

    async def open_store() -> tuple[MemoryTelegramChannel, MemoryTelegramChannel]:
        return store, store

    logs: list[str] = []
    deps = _deps(
        _Hits(),
        env=_env(ANTHROPIC_API_KEY="key"),
        open_channel=open_store,
        sender=_Sender(),
        plans=MemoryPlanStore(),
        model=_Model(),
        clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        logs=logs,
    )
    response = _post(deps, _message(update_id=8, text="tin"), _HEADER)
    assert response.status_code == 200
    assert response.content == b""
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "done", "replied", 8, None)


def test_route_defer_logs_store_unavailable() -> None:
    async def open_channel() -> tuple[object, object]:
        raise RuntimeError("kho")

    logs: list[str] = []
    response = _post(
        _deps(_Hits(), open_channel=open_channel, logs=logs),
        _message(update_id=9, text=_TEXT),
        _HEADER,
    )
    assert response.status_code == 503
    assert response.content == b""
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "defer", "store_unavailable", 9, "RuntimeError")


def test_route_bool_update_id_is_bad_ids() -> None:
    body = {
        "update_id": True,
        "message": {
            "message_id": 1,
            "text": _TEXT,
            "chat": {"id": 7, "type": "private"},
            "from": {"id": 123},
        },
    }
    logs: list[str] = []
    response = _post(_deps(_Hits(), logs=logs), body, _HEADER)
    assert response.status_code == 200
    assert response.content == b""
    items = _outcome_lines(logs)
    assert len(items) == 1
    _assert_channel(items[0], "ignore", "bad_ids", None, None)
