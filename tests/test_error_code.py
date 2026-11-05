"""error_code_of và dòng kênh khi kho ném APIError. Không mở mạng."""

import asyncio
import json
from datetime import datetime

import httpx
import pytest
from postgrest.exceptions import APIError

from api.telegram_update import Inbound, Outcome, handle_update
from core.log_line import error_code_of
from tests.fakes.memory_telegram_channel import MemoryTelegramChannel
from tests.test_telegram_update_flow import (
    BoomPlans,
    Clock,
    RecordingSender,
    ScriptModel,
    _CHAT,
    _START,
    _reply,
)

_MARKER = "SECRET-MARKER"
_KEYS = ["outcome", "reason", "update_id", "error_type", "error_code"]


def _api(code: object) -> APIError:
    return APIError(
        {
            "message": f"m {_MARKER}",
            "code": code,
            "hint": f"h {_MARKER}",
            "details": f"d {_MARKER}",
        }
    )


def test_error_code_of_keeps_only_a_short_code() -> None:
    assert error_code_of(_api(401)) == "401"
    assert error_code_of(_api("PGRST202")) == "PGRST202"
    assert error_code_of(_api(None)) is None
    assert error_code_of(_api("")) is None
    assert error_code_of(_api("A" * 40)) is None
    assert error_code_of(_api("a b")) is None
    assert error_code_of(_api(True)) is None
    assert error_code_of(RuntimeError("boom")) is None
    assert error_code_of(httpx.ConnectTimeout("timed out")) is None


class _Boom(MemoryTelegramChannel):
    def __init__(self, method: str, error: BaseException) -> None:
        super().__init__()
        self._method = method
        self._error = error

    async def claim(self, update_id: int, started_at: datetime):
        if self._method == "claim":
            raise self._error
        return await super().claim(update_id, started_at)

    async def save_reply_if_absent(self, update_id: int, reply: str) -> bool:
        if self._method == "save_reply_if_absent":
            raise self._error
        return await super().save_reply_if_absent(update_id, reply)

    async def append_once(
        self,
        update_id: int,
        role: str,
        chat_id: int,
        body: str,
        saved_at: datetime,
    ) -> None:
        if self._method == "append_once":
            raise self._error
        await super().append_once(update_id, role, chat_id, body, saved_at)

    async def mark_sent(self, update_id: int, sent_at: datetime) -> None:
        if self._method == "mark_sent":
            raise self._error
        await super().mark_sent(update_id, sent_at)

    async def list_recent(self, chat_id: int, saved_at_gte: datetime, limit: int):
        if self._method == "list_recent":
            raise self._error
        return await super().list_recent(chat_id, saved_at_gte, limit)


@pytest.mark.parametrize(
    ("method", "reason"),
    [
        ("claim", "store_unavailable"),
        ("save_reply_if_absent", "reply_not_saved"),
        ("append_once", "context_failed"),
        ("mark_sent", "send_failed"),
        ("list_recent", "context_failed"),
    ],
)
def test_store_api_error_logs_code_without_body(method: str, reason: str) -> None:
    async def scenario() -> None:
        store = _Boom(method, _api(401))
        logs: list[str] = []

        async def open_channel():
            return store, store

        outcome = await handle_update(
            Inbound(update_id=15, chat_id=_CHAT, text="tin"),
            open_channel=open_channel,
            sender=RecordingSender(),
            plans=BoomPlans(),
            client=ScriptModel([_reply("xong", "end_turn")]),
            api_key="caller-key",
            clock=Clock(_START),
            log=logs.append,
        )
        assert outcome is Outcome.Defer
        channel = [json.loads(line) for line in logs if '"outcome"' in line]
        assert len(channel) == 1
        assert list(channel[0]) == _KEYS
        assert channel[0]["outcome"] == "defer"
        assert channel[0]["reason"] == reason
        assert channel[0]["update_id"] == 15
        assert channel[0]["error_type"] == "APIError"
        assert channel[0]["error_code"] == "401"
        assert _MARKER not in "\n".join(logs)

    asyncio.run(scenario())
