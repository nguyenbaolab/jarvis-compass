"""Client gửi: JSON đúng hai khóa, timeout 10 giây, lỗi không chứa token."""

import json

import httpx
import pytest

from clients.telegram import TelegramSendError, TelegramSenderClient

_TOKEN = "bot-token-khong-duoc-lo"


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def test_send_message_json_has_chat_id_and_text_only() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True})

    sender = TelegramSenderClient(_TOKEN, transport=_transport(handler))
    import asyncio

    asyncio.run(sender.send_part(7, "một *hai* _ba_ `bon`"))
    assert seen["body"] == {"chat_id": 7, "text": "một *hai* _ba_ `bon`"}
    assert set(seen["body"]) == {"chat_id", "text"}
    assert "parse_mode" not in seen["body"]
    assert str(seen["url"]).endswith(f"/bot{_TOKEN}/sendMessage")


def test_send_failure_raises_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    timeouts: list[object] = []

    class _Capture(httpx.AsyncClient):
        def __init__(self, *args: object, **kwargs: object) -> None:
            timeouts.append(kwargs.get("timeout"))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("clients.telegram.httpx.AsyncClient", _Capture)

    def _status(code: int, body: dict[str, object]) -> httpx.MockTransport:
        return httpx.MockTransport(lambda _request: httpx.Response(code, json=body))

    import asyncio

    sender = TelegramSenderClient(_TOKEN, transport=_status(500, {"ok": False}))
    with pytest.raises(TelegramSendError) as caught:
        asyncio.run(sender.send_part(7, "câu"))
    assert _TOKEN not in str(caught.value)
    assert timeouts[-1] == 10.0

    sender = TelegramSenderClient(_TOKEN, transport=_status(200, {"ok": False}))
    with pytest.raises(TelegramSendError) as caught:
        asyncio.run(sender.send_part(7, "câu"))
    assert _TOKEN not in str(caught.value)

    def _boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    sender = TelegramSenderClient(_TOKEN, transport=httpx.MockTransport(_boom))
    with pytest.raises(TelegramSendError) as caught:
        asyncio.run(sender.send_part(7, "câu"))
    assert _TOKEN not in str(caught.value)
