"""POST /telegram. Từ chối 401, Hoãn 503, Bỏ qua và xong 200, body rỗng."""

import json

import pytest
from fastapi.testclient import TestClient

from api.routes_telegram import current_deps
from app import app
from config.settings import SettingsError
from core.llm import ModelResponse, ToolRequest
from tests.fakes.memory_plan_store import MemoryPlanStore
from tests.fakes.memory_telegram_channel import MemoryTelegramChannel
from tests.test_llm_turn import _LOG_KEYS as _MODEL_KEYS
from tests.test_tool_router import _LOG_KEYS as _TOOL_KEYS

_SECRET = "secret-dung"
_WRONG = "secret-sai"
_TOKEN = "token-khong-log"
_OWNER = "123"


def _message(update_id: int = 1, text: str = "xin chao", user_id: int = 123, chat_type: str = "private") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "text": text,
            "chat": {"id": 7, "type": chat_type},
            "from": {"id": user_id},
        },
    }


class _Hits:
    def __init__(self) -> None:
        self.update = 0
        self.context = 0
        self.plan = 0
        self.model = 0
        self.send = 0

    def zeros(self) -> None:
        assert (self.update, self.context, self.plan, self.model, self.send) == (0, 0, 0, 0, 0)


class _GuardPlans(MemoryPlanStore):
    def __init__(self, hits: _Hits) -> None:
        super().__init__()
        self._hits = hits

    async def add(self, goal: str, subtasks: tuple) -> object:
        self._hits.plan += 1
        raise AssertionError("kho kế hoạch")

    async def list_newest_first(self) -> tuple:
        self._hits.plan += 1
        raise AssertionError("kho kế hoạch")

    async def get(self, plan_id: str) -> object:
        self._hits.plan += 1
        raise AssertionError("kho kế hoạch")

    async def replace(self, plan: object) -> None:
        self._hits.plan += 1
        raise AssertionError("kho kế hoạch")


class _GuardModel:
    def __init__(self, hits: _Hits) -> None:
        self._hits = hits
        self.model = "guard"

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del request, api_key, timeout
        self._hits.model += 1
        raise AssertionError("mô hình")


class _GuardSender:
    def __init__(self, hits: _Hits) -> None:
        self._hits = hits

    async def send_part(self, chat_id: int, text: str) -> None:
        del chat_id, text
        self._hits.send += 1
        raise AssertionError("gửi")


def _guard_open(hits: _Hits):
    async def open_channel():
        hits.update += 1
        hits.context += 1
        raise AssertionError("cổng")

    return open_channel


def _env(**extra: str) -> dict[str, str]:
    base = {
        "TELEGRAM_WEBHOOK_SECRET": _SECRET,
        "TELEGRAM_BOT_TOKEN": _TOKEN,
        "TELEGRAM_OWNER_ID": _OWNER,
    }
    base.update(extra)
    return base


def _deps(hits: _Hits, env: dict[str, str] | None = None, **kwargs: object):
    from api.routes_telegram import TelegramDeps

    return TelegramDeps(
        env=_env() if env is None else env,
        clock=kwargs.get("clock"),
        open_channel=kwargs.get("open_channel", _guard_open(hits)),
        sender=kwargs.get("sender", _GuardSender(hits)),
        plans=kwargs.get("plans", _GuardPlans(hits)),
        model=kwargs.get("model", _GuardModel(hits)),
        logs=kwargs.get("logs"),
    )


def _post(deps: object, body: object, headers: dict[str, str] | None, *, raw: bytes | None = None) -> object:
    app.dependency_overrides[current_deps] = lambda: deps
    client = TestClient(app)
    try:
        if raw is not None:
            return client.post("/telegram", content=raw, headers={"content-type": "application/json", **(headers or {})})
        return client.post("/telegram", json=body, headers=headers)
    finally:
        app.dependency_overrides.clear()


def test_reject_is_401_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    import hmac

    seen: list[tuple[str, str]] = []

    def _spy(left: str, right: str) -> bool:
        seen.append((left, right))
        return hmac.compare_digest(left, right)

    monkeypatch.setattr("api.routes_telegram.hmac.compare_digest", _spy)
    hits = _Hits()
    missing_secret = _deps(hits, env={"TELEGRAM_BOT_TOKEN": _TOKEN, "TELEGRAM_OWNER_ID": _OWNER})
    response = _post(missing_secret, _message(), {_HEADER(_SECRET): _SECRET})
    assert response.status_code == 401
    assert response.content == b""
    hits.zeros()

    hits = _Hits()
    response = _post(_deps(hits), _message(), {"X-Telegram-Bot-Api-Secret-Token": _WRONG})
    assert response.status_code == 401
    assert response.content == b""
    assert seen[-1] == (_SECRET, _WRONG)
    hits.zeros()

    hits = _Hits()
    monkeypatch.setattr("api.routes_telegram.header_secret", lambda _request: 123)
    response = _post(_deps(hits), _message(), {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
    assert response.status_code == 401
    assert response.content == b""
    hits.zeros()

    hits = _Hits()
    no_token = _deps(hits, env={"TELEGRAM_WEBHOOK_SECRET": _SECRET, "TELEGRAM_OWNER_ID": _OWNER})
    response = _post(no_token, _message(), {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
    assert response.status_code == 401
    assert response.content == b""
    hits.zeros()


def _HEADER(value: str) -> str:
    del value
    return "X-Telegram-Bot-Api-Secret-Token"


def test_skip_is_200_empty() -> None:
    cases = (
        {"update_id": 1, "edited_message": {"text": "sửa", "chat": {"id": 7, "type": "private"}, "from": {"id": 123}}},
        {"update_id": 2, "callback_query": {"id": "nút"}},
        _message(chat_type="group"),
        _message(user_id=999),
        ["không phải object"],
    )
    for body in cases:
        hits = _Hits()
        response = _post(_deps(hits), body, {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
        assert response.status_code == 200
        assert response.content == b""
        hits.zeros()

    hits = _Hits()
    missing_owner = _deps(hits, env={"TELEGRAM_WEBHOOK_SECRET": _SECRET, "TELEGRAM_BOT_TOKEN": _TOKEN})
    response = _post(missing_owner, _message(), {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
    assert response.status_code == 200
    assert response.content == b""
    hits.zeros()

    hits = _Hits()
    response = _post(_deps(hits), None, {"X-Telegram-Bot-Api-Secret-Token": _SECRET}, raw=b"{")
    assert response.status_code == 200
    assert response.content == b""
    hits.zeros()


def test_defer_is_503_done_is_200() -> None:
    from datetime import datetime, timezone

    hits = _Hits()

    async def open_channel():
        raise SettingsError("Thiếu SUPABASE_URL.")

    response = _post(
        _deps(hits, open_channel=open_channel),
        _message(),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 503
    assert response.content == b""

    store = MemoryTelegramChannel()
    sender_parts: list[tuple[int, str]] = []

    class _Sender:
        async def send_part(self, chat_id: int, text: str) -> None:
            sender_parts.append((chat_id, text))

    class _Model:
        def __init__(self) -> None:
            self.model = "scripted"
            self.calls = 0

        async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
            del request, api_key, timeout
            self.calls += 1
            return ModelResponse("xong", (), "end_turn", 1, 1, "scripted")

    async def open_store():
        return store, store

    model = _Model()
    deps = _deps(
        _Hits(),
        env=_env(ANTHROPIC_API_KEY="key"),
        open_channel=open_store,
        sender=_Sender(),
        plans=MemoryPlanStore(),
        model=model,
        clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    headers = {"X-Telegram-Bot-Api-Secret-Token": _SECRET}
    first = _post(deps, _message(text="tin"), headers)
    assert first.status_code == 200
    assert first.content == b""
    assert sender_parts == [(7, "xong")]
    assert model.calls == 1
    second = _post(deps, _message(text="tin"), headers)
    assert second.status_code == 200
    assert second.content == b""
    assert sender_parts == [(7, "xong")]
    assert model.calls == 1


def test_channel_log_has_no_secret_or_text(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import logging

    import httpx

    from clients.telegram import TelegramSenderClient

    caplog.set_level(logging.DEBUG)
    texts = "tin rieng khong log"
    reply = "cau khong log"

    def absent(response: object, logs: list[str]) -> None:
        captured = capsys.readouterr()
        blob = "\n".join(
            [caplog.text, captured.out, captured.err, "\n".join(logs), bytes(response.content).decode()]
        )
        for forbidden in (_SECRET, _WRONG, _TOKEN, texts, reply):
            assert forbidden not in blob

    logs: list[str] = []
    hits = _Hits()
    response = _post(
        _deps(hits, logs=logs),
        _message(text=texts),
        {"X-Telegram-Bot-Api-Secret-Token": _WRONG},
    )
    assert response.status_code == 401
    absent(response, logs)

    from datetime import datetime, timezone

    store = MemoryTelegramChannel()

    class _Model:
        def __init__(self) -> None:
            self.model = "scripted"
            self._steps = [
                ModelResponse(
                    "",
                    (ToolRequest(id="t-create", name="create_plan", tool_input={"goal": "Hoc"}),),
                    "tool_use",
                    1,
                    1,
                    "scripted",
                ),
                ModelResponse(reply, (), "end_turn", 1, 1, "scripted"),
            ]

        async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
            del request, api_key, timeout
            return self._steps.pop(0)

    async def open_store():
        return store, store

    def _ok(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"ok": True})

    channel_logs: list[str] = []
    deps = _deps(
        _Hits(),
        env=_env(ANTHROPIC_API_KEY="key"),
        open_channel=open_store,
        sender=TelegramSenderClient(_TOKEN, transport=httpx.MockTransport(_ok)),
        plans=MemoryPlanStore(),
        model=_Model(),
        logs=channel_logs,
        clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    done = _post(deps, _message(text=texts), {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
    assert done.status_code == 200
    absent(done, channel_logs)
    parsed = [json.loads(line) for line in channel_logs]
    tool_lines = [item for item in parsed if "tool" in item and "prompt_version" not in item]
    model_lines = [item for item in parsed if "prompt_version" in item]
    assert tool_lines
    assert model_lines
    assert list(tool_lines[0]) == list(_TOOL_KEYS)
    assert list(model_lines[0]) == list(_MODEL_KEYS)


class _AttrEnv:
    """Giống env của Worker: thuộc tính, không phải Mapping."""

    def __init__(self) -> None:
        self.TELEGRAM_WEBHOOK_SECRET = _SECRET
        self.TELEGRAM_BOT_TOKEN = _TOKEN
        self.TELEGRAM_OWNER_ID = _OWNER


def _post_scope(env: object, body: object, headers: dict[str, str] | None, *, set_env: bool) -> object:
    async def asgi(scope, receive, send):
        if set_env and scope.get("type") == "http":
            scope["env"] = env
        await app(scope, receive, send)

    client = TestClient(asgi)
    return client.post("/telegram", json=body, headers=headers)


@pytest.mark.parametrize(
    "case_id",
    [
        "attribute_env_correct_secret_group",
        "attribute_env_wrong_secret",
        "dict_env_correct_secret_group",
        "scope_without_env",
        "scope_env_none",
    ],
)
def test_scope_env_shape(case_id: str) -> None:
    group = _message(chat_type="group")
    if case_id == "attribute_env_correct_secret_group":
        response = _post_scope(_AttrEnv(), group, {"X-Telegram-Bot-Api-Secret-Token": _SECRET}, set_env=True)
        assert response.status_code == 200
    elif case_id == "attribute_env_wrong_secret":
        response = _post_scope(_AttrEnv(), group, {"X-Telegram-Bot-Api-Secret-Token": _WRONG}, set_env=True)
        assert response.status_code == 401
    elif case_id == "dict_env_correct_secret_group":
        response = _post_scope(_env(), group, {"X-Telegram-Bot-Api-Secret-Token": _SECRET}, set_env=True)
        assert response.status_code == 200
    elif case_id == "scope_without_env":
        response = _post_scope(None, group, {"X-Telegram-Bot-Api-Secret-Token": _SECRET}, set_env=False)
        assert response.status_code == 401
    else:
        response = _post_scope(None, group, {"X-Telegram-Bot-Api-Secret-Token": _SECRET}, set_env=True)
        assert response.status_code == 401
    assert response.content == b""


def test_default_path_without_supabase_is_503() -> None:
    hits = _Hits()
    deps = _deps(
        hits,
        env=_env(),
        open_channel=None,
        plans=None,
        sender=_GuardSender(hits),
        model=_GuardModel(hits),
    )
    response = _post(deps, _message(text="tin chu"), {"X-Telegram-Bot-Api-Secret-Token": _SECRET})
    assert response.status_code == 503
    assert response.content == b""
    assert hits.send == 0
    assert hits.model == 0


def test_claim_error_is_503() -> None:
    from datetime import datetime, timezone

    hits = _Hits()

    class _BoomClaim(MemoryTelegramChannel):
        async def claim(self, update_id: int, started_at: datetime) -> object:
            raise RuntimeError("claim")

    async def open_channel():
        store = _BoomClaim()
        return store, store

    response = _post(
        _deps(
            hits,
            open_channel=open_channel,
            sender=_GuardSender(hits),
            model=_GuardModel(hits),
            plans=MemoryPlanStore(),
            clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        ),
        _message(text="tin chu"),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 503
    assert response.content == b""


def test_clock_error_is_503() -> None:
    hits = _Hits()
    store = MemoryTelegramChannel()

    async def open_channel():
        return store, store

    def clock() -> object:
        raise RuntimeError("đồng hồ")

    response = _post(
        _deps(
            hits,
            open_channel=open_channel,
            sender=_GuardSender(hits),
            model=_GuardModel(hits),
            plans=MemoryPlanStore(),
            clock=clock,
        ),
        _message(text="tin chu"),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 503
    assert response.content == b""


def test_send_error_is_503() -> None:
    from datetime import datetime, timezone

    from clients.telegram import TelegramSendError

    store = MemoryTelegramChannel()

    class _Sender:
        async def send_part(self, chat_id: int, text: str) -> None:
            del chat_id, text
            raise TelegramSendError("Gửi không thành công.")

    class _Model:
        def __init__(self) -> None:
            self.model = "scripted"

        async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
            del request, api_key, timeout
            return ModelResponse("xong", (), "end_turn", 1, 1, "scripted")

    async def open_store():
        return store, store

    response = _post(
        _deps(
            _Hits(),
            env=_env(ANTHROPIC_API_KEY="key"),
            open_channel=open_store,
            sender=_Sender(),
            plans=MemoryPlanStore(),
            model=_Model(),
            clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        ),
        _message(text="tin"),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 503
    assert response.content == b""


def _media_message(case_id: str) -> dict:
    message: dict[str, object] = {
        "message_id": 1,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 123},
    }
    if case_id == "voice":
        message["voice"] = {"file_id": "v", "duration": 1}
    elif case_id == "photo":
        message["photo"] = [{"file_id": "p", "width": 1, "height": 1}]
    elif case_id == "photo_caption":
        message["photo"] = [{"file_id": "p", "width": 1, "height": 1}]
        message["caption"] = "xin chào"
    elif case_id == "sticker":
        message["sticker"] = {"file_id": "s"}
    elif case_id == "location":
        message["location"] = {"latitude": 1.0, "longitude": 2.0}
    elif case_id == "contact":
        message["contact"] = {"phone_number": "+1", "first_name": "A"}
    elif case_id == "poll":
        message["poll"] = {"id": "1", "question": "?", "options": []}
    else:
        message["document"] = {"file_id": "d"}
    assert "text" not in message
    return {"update_id": 1, "message": message}


@pytest.mark.parametrize(
    "case_id",
    ["voice", "photo", "photo_caption", "sticker", "location", "contact", "poll", "document"],
)
def test_real_non_text_body_gets_fixed_sentence(case_id: str) -> None:
    import asyncio
    from datetime import datetime, timedelta, timezone

    hits = _Hits()
    store = MemoryTelegramChannel()
    parts: list[tuple[int, str]] = []

    class _Sender:
        async def send_part(self, chat_id: int, text: str) -> None:
            parts.append((chat_id, text))

    async def open_store():
        return store, store

    response = _post(
        _deps(
            hits,
            open_channel=open_store,
            sender=_Sender(),
            plans=_GuardPlans(hits),
            model=_GuardModel(hits),
            clock=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        ),
        _media_message(case_id),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 200
    assert response.content == b""
    assert parts == [(42, "Mình chỉ đọc được tin chữ.")]
    assert hits.model == 0
    assert hits.plan == 0
    rows = asyncio.run(store.list_recent(42, datetime(2026, 6, 1, tzinfo=timezone.utc) - timedelta(hours=1), 20))
    assert rows == ()


@pytest.mark.parametrize("case_id", ["supergroup", "channel"])
def test_supergroup_and_channel_touch_nothing(case_id: str) -> None:
    hits = _Hits()
    response = _post(
        _deps(hits),
        _message(chat_type=case_id),
        {"X-Telegram-Bot-Api-Secret-Token": _SECRET},
    )
    assert response.status_code == 200
    assert response.content == b""
    hits.zeros()


def test_wrong_secret_rejects_before_foreign_sender() -> None:
    hits = _Hits()
    response = _post(
        _deps(hits),
        _message(user_id=999),
        {"X-Telegram-Bot-Api-Secret-Token": _WRONG},
    )
    assert response.status_code == 401
    assert response.content == b""
    hits.zeros()


def test_missing_secret_header_is_401() -> None:
    hits = _Hits()
    response = _post(_deps(hits), _message(), {})
    assert response.status_code == 401
    assert response.content == b""
    hits.zeros()
