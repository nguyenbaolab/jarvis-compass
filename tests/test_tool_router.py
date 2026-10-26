"""Lớp điều phối: đúng tool, đầu vào sai, câu miền, và một dòng nhật ký."""

import asyncio
import json

import pytest

from core.plans import Plan, PlanDomainError, Subtask
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.plan_tools import create_plan, get_plans
from tools.tool_definitions import DEFINITIONS_VERSION, TOOL_DEFINITIONS
from tools.tool_router import execute_tool

_LOG_KEYS = [
    "tool",
    "input",
    "ok",
    "error_type",
    "duration_ms",
    "definitions_version",
    "detail",
]
_UNKNOWN = "Không có tool với tên này."
_NOT_OBJECT = "Đầu vào phải là một object."
_UNEXPECTED = "Không thực hiện được yêu cầu này."
_MISSING_PLAN = "Không có kế hoạch với danh tính này."
_MISSING_SUBTASK = "Kế hoạch này không có việc con với danh tính này."
_BAD_STATUS = "Trạng thái việc con đã lưu không hợp lệ."
_EMPTY_GOAL = "Mục tiêu không được để trống."
_BAD_STATUS_WORD = "Trạng thái việc con chỉ nhận pending, done hoặc skipped."


class GuardStore(MemoryPlanStore):
    """Ghi mọi lời gọi kho. Ca tên lạ và ca đầu vào sai phải để danh sách rỗng."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    async def add(self, goal: str, subtasks: tuple[Subtask, ...]) -> Plan:
        self.calls.append("add")
        return await super().add(goal, subtasks)

    async def list_newest_first(self) -> tuple[Plan, ...]:
        self.calls.append("list_newest_first")
        return await super().list_newest_first()

    async def get(self, plan_id: str) -> Plan | None:
        self.calls.append("get")
        return await super().get(plan_id)

    async def replace(self, plan: Plan) -> None:
        self.calls.append("replace")
        await super().replace(plan)


class BoomStore(MemoryPlanStore):
    """Ném lỗi đã chọn từ đúng một phương thức."""

    def __init__(self, error: BaseException, method: str) -> None:
        super().__init__()
        self._error = error
        self._method = method

    async def list_newest_first(self) -> tuple[Plan, ...]:
        if self._method == "list_newest_first":
            raise self._error
        return await super().list_newest_first()

    async def get(self, plan_id: str) -> Plan | None:
        if self._method == "get":
            raise self._error
        return await super().get(plan_id)


def _run(name: object, tool_input: object, store: MemoryPlanStore):
    """Một lần gọi, đúng một dòng log, rồi trả kết quả, dòng thô, và object."""

    lines: list[str] = []
    result = asyncio.run(execute_tool(name, tool_input, store=store, log=lines.append))
    assert len(lines) == 1
    assert "\n" not in lines[0]
    assert isinstance(lines[0], str)
    logged = json.loads(lines[0])
    assert list(logged) == _LOG_KEYS
    assert logged["definitions_version"] == 1
    assert isinstance(logged["definitions_version"], int)
    assert isinstance(logged["duration_ms"], int)
    assert logged["duration_ms"] >= 0
    assert logged["duration_ms"] < 3000
    assert logged["tool"] == name
    assert logged["ok"] is result.success
    return result, lines[0], logged


def test_catalog_matches_contract() -> None:
    assert DEFINITIONS_VERSION == 1
    assert isinstance(DEFINITIONS_VERSION, int)
    assert list(TOOL_DEFINITIONS) == [
        "create_plan",
        "get_plans",
        "get_plan_detail",
        "update_subtask",
        "add_subtask",
        "set_subtask_note",
    ]
    descriptions = {
        "create_plan": "Tạo một kế hoạch mới từ mục tiêu và danh sách việc con.",
        "get_plans": "Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu.",
        "get_plan_detail": "Mở một kế hoạch theo danh tính.",
        "update_subtask": "Đặt trạng thái một việc con thành pending, done hoặc skipped.",
        "add_subtask": "Thêm một việc con vào cuối một kế hoạch.",
        "set_subtask_note": "Đặt hoặc xóa ghi chú của một việc con.",
    }
    for name, description in descriptions.items():
        entry = TOOL_DEFINITIONS[name]
        assert entry["description"] == description
        schema = entry["input_schema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
    assert TOOL_DEFINITIONS["create_plan"]["input_schema"]["required"] == ["goal"]
    assert list(TOOL_DEFINITIONS["create_plan"]["input_schema"]["properties"]) == ["goal", "subtasks"]
    subtasks = TOOL_DEFINITIONS["create_plan"]["input_schema"]["properties"]["subtasks"]
    assert subtasks["type"] == "array"
    assert subtasks["items"]["type"] == "string"
    assert TOOL_DEFINITIONS["get_plans"]["input_schema"]["required"] == []
    assert list(TOOL_DEFINITIONS["get_plans"]["input_schema"]["properties"]) == ["keyword"]
    assert "enum" not in TOOL_DEFINITIONS["update_subtask"]["input_schema"]["properties"]["status"]


def test_unknown_name_does_not_call_store() -> None:
    store = GuardStore()
    for name in ("revise_plan", "Create_plan", ""):
        result, _line, logged = _run(name, {}, store)
        assert result.success is False
        assert result.output == _UNKNOWN
        assert logged["error_type"] == "unknown_tool"
        assert logged["detail"] is None
    assert store.calls == []


@pytest.mark.parametrize("tool_input", [["không phải object"], "chuỗi", None, 3])
def test_input_must_be_object(tool_input: object) -> None:
    store = GuardStore()
    result, _line, logged = _run("get_plans", tool_input, store)
    assert result.success is False
    assert result.output == _NOT_OBJECT
    assert logged["error_type"] == "invalid_input"
    assert store.calls == []


def test_each_tool_has_wrong_type_and_missing_or_extra() -> None:
    cases = [
        ("create_plan", {"goal": "Học", "subtasks": ["Học hiragana", None]}, "Một phần tử của trường subtasks sai kiểu."),
        ("create_plan", {"subtasks": ["Học hiragana"]}, "Đầu vào thiếu trường goal."),
        ("get_plans", {"keyword": 1}, "Trường keyword sai kiểu."),
        ("get_plans", {"limit": 1}, "Đầu vào thừa trường limit."),
        ("get_plan_detail", {"plan_id": 1}, "Trường plan_id sai kiểu."),
        ("get_plan_detail", {}, "Đầu vào thiếu trường plan_id."),
        ("update_subtask", {"plan_id": "a", "subtask_id": "b", "status": 1}, "Trường status sai kiểu."),
        ("update_subtask", {"plan_id": "a", "subtask_id": "b"}, "Đầu vào thiếu trường status."),
        ("add_subtask", {"plan_id": "a", "title": 1}, "Trường title sai kiểu."),
        ("add_subtask", {"plan_id": "a"}, "Đầu vào thiếu trường title."),
        ("set_subtask_note", {"plan_id": "a", "subtask_id": "b", "note": 1}, "Trường note sai kiểu."),
        ("set_subtask_note", {"plan_id": "a", "subtask_id": "b"}, "Đầu vào thiếu trường note."),
    ]
    for name, tool_input, output in cases:
        store = GuardStore()
        result, _line, logged = _run(name, tool_input, store)
        assert result.success is False
        assert result.output == output
        assert logged["error_type"] == "invalid_input"
        assert logged["detail"] is None
        assert store.calls == []


def test_extra_field_wins_over_missing_field() -> None:
    store = GuardStore()
    result, _line, logged = _run(
        "update_subtask",
        {"plan_id": "a", "subtask_id": "b", "limit": 1},
        store,
    )
    assert result.output == "Đầu vào thừa trường limit."
    assert logged["error_type"] == "invalid_input"
    assert store.calls == []


def test_empty_goal_keeps_domain_sentence() -> None:
    store = GuardStore()
    result, _line, logged = _run("create_plan", {"goal": ""}, store)
    assert result.success is False
    assert result.output == _EMPTY_GOAL
    assert logged["error_type"] == "domain"
    assert store.calls == []


def test_missing_plan_keeps_domain_sentence() -> None:
    store = GuardStore()
    result, _line, logged = _run("get_plan_detail", {"plan_id": "khong-co"}, store)
    assert result.success is False
    assert result.output == _MISSING_PLAN
    assert logged["error_type"] == "domain"


def test_missing_subtask_keeps_domain_sentence() -> None:
    store = MemoryPlanStore()
    created = json.loads(
        asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store)).output
    )
    result, _line, logged = _run(
        "update_subtask",
        {"plan_id": created["id"], "subtask_id": "khong-co", "status": "done"},
        store,
    )
    assert result.success is False
    assert result.output == _MISSING_SUBTASK
    assert logged["error_type"] == "domain"
    assert logged["detail"] is None


def test_stored_status_domain_error_keeps_sentence() -> None:
    store = BoomStore(PlanDomainError(_BAD_STATUS), "get")
    result, _line, logged = _run("get_plan_detail", {"plan_id": "khong-co"}, store)
    assert result.success is False
    assert result.output == _BAD_STATUS
    assert logged["error_type"] == "domain"
    assert logged["detail"] is None


def test_unexpected_hides_message_and_logs_class_name() -> None:
    store = BoomStore(RuntimeError("secret-key-value"), "list_newest_first")
    result, line, logged = _run("get_plans", {}, store)
    assert result.success is False
    assert result.output == _UNEXPECTED
    assert "secret-key-value" not in result.output
    assert "RuntimeError" not in result.output
    assert "secret-key-value" not in line
    assert logged["error_type"] == "unexpected"
    assert logged["detail"] == "RuntimeError"


def test_keyboard_interrupt_escapes_without_result_or_log() -> None:
    store = BoomStore(KeyboardInterrupt(), "list_newest_first")
    lines: list[str] = []
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(execute_tool("get_plans", {}, store=store, log=lines.append))
    assert lines == []


def test_get_plans_output_matches_direct_call() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", ["Học hiragana"], store=store))
    direct = asyncio.run(get_plans(store=store))
    result, line, logged = _run("get_plans", {}, store)
    assert result.success is True
    assert result.output == direct.output
    assert logged["error_type"] is None
    assert logged["detail"] is None
    assert logged["input"] == {}


def test_valid_calls_dispatch_each_tool() -> None:
    store = MemoryPlanStore()
    created_result, line, _logged = _run(
        "create_plan",
        {"goal": "Học tiếng Nhật", "subtasks": ["Học hiragana"]},
        store,
    )
    assert "Học tiếng Nhật" in line
    assert "\\u" not in line
    assert created_result.success is True
    created = json.loads(created_result.output)
    detail, _line, _logged = _run("get_plan_detail", {"plan_id": created["id"]}, store)
    assert detail.success is True
    assert detail.output == created_result.output
    updated, _line, _logged = _run(
        "update_subtask",
        {"plan_id": created["id"], "subtask_id": created["subtasks"][0]["id"], "status": "done"},
        store,
    )
    assert updated.success is True
    assert json.loads(updated.output)["subtasks"][0]["status"] == "done"
    added, _line, _logged = _run(
        "add_subtask",
        {"plan_id": created["id"], "title": "Luyện 10 phút"},
        store,
    )
    assert added.success is True
    titles = [item["title"] for item in json.loads(added.output)["subtasks"]]
    assert titles[-1] == "Luyện 10 phút"
    noted, _line, _logged = _run(
        "set_subtask_note",
        {
            "plan_id": created["id"],
            "subtask_id": created["subtasks"][0]["id"],
            "note": "mỗi sáng",
        },
        store,
    )
    assert noted.success is True
    assert json.loads(noted.output)["subtasks"][0]["note"] == "mỗi sáng"


def test_duration_floors_monotonic_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter((10.0, 10.0029))
    monkeypatch.setattr("tools.tool_router._now", lambda: next(ticks))
    store = MemoryPlanStore()
    lines: list[str] = []
    asyncio.run(execute_tool("get_plans", {}, store=store, log=lines.append))
    assert json.loads(lines[0])["duration_ms"] == 2


def test_unserializable_input_logs_null_and_still_returns() -> None:
    store = GuardStore()
    lines: list[str] = []
    result = asyncio.run(
        execute_tool(
            "create_plan",
            {"goal": "Học", "subtasks": [object()]},
            store=store,
            log=lines.append,
        )
    )
    assert result.success is False
    assert result.output == "Một phần tử của trường subtasks sai kiểu."
    logged = json.loads(lines[0])
    assert logged["input"] is None
    assert store.calls == []


def _deep_value() -> dict:
    """Dict lồng sâu hơn giới hạn đệ quy, dumps sẽ ném RecursionError."""

    node: object = "lá"
    for _ in range(5000):
        node = {"n": node}
    return {"goal": node}


def test_dispatch_names_match_catalog() -> None:
    from tools import tool_router

    assert set(tool_router._DISPATCH) == set(TOOL_DEFINITIONS)


@pytest.mark.parametrize("name", [None, 3, object()], ids=["none", "number", "object"])
def test_non_string_name_logs_null_tool(name: object) -> None:
    store = GuardStore()
    lines: list[str] = []
    result = asyncio.run(execute_tool(name, {}, store=store, log=lines.append))
    assert result.success is False
    assert result.output == _UNKNOWN
    assert len(lines) == 1
    logged = json.loads(lines[0])
    assert logged["tool"] is None
    assert logged["error_type"] == "unknown_tool"
    assert store.calls == []


def test_deep_input_logs_null_and_returns() -> None:
    store = GuardStore()
    lines: list[str] = []
    result = asyncio.run(
        execute_tool("create_plan", _deep_value(), store=store, log=lines.append)
    )
    assert result.success is False
    assert len(lines) == 1
    assert json.loads(lines[0])["input"] is None
    assert store.calls == []


def test_log_failure_still_returns_result() -> None:
    def fail(_line: str) -> None:
        raise OSError("disk full")

    result = asyncio.run(execute_tool("get_plans", {}, store=MemoryPlanStore(), log=fail))
    assert result.success is True


def test_unknown_name_beats_non_object() -> None:
    store = GuardStore()
    result, _line, logged = _run("revise_plan", ["không phải object"], store)
    assert result.output == _UNKNOWN
    assert logged["error_type"] == "unknown_tool"
    assert store.calls == []


def test_first_extra_key_in_object_order() -> None:
    store = GuardStore()
    result, _line, _logged = _run(
        "update_subtask",
        {"zz": 1, "aa": 2, "plan_id": "a", "subtask_id": "b", "status": "done"},
        store,
    )
    assert result.output == "Đầu vào thừa trường zz."
    assert store.calls == []


def test_first_missing_follows_schema_order() -> None:
    store = GuardStore()
    result, _line, _logged = _run("update_subtask", {"status": "done"}, store)
    assert result.output == "Đầu vào thiếu trường plan_id."
    assert store.calls == []


def test_missing_beats_wrong_type() -> None:
    store = GuardStore()
    result, _line, _logged = _run(
        "update_subtask",
        {"plan_id": 1, "status": "done"},
        store,
    )
    assert result.output == "Đầu vào thiếu trường subtask_id."
    assert store.calls == []


def test_first_wrong_type_follows_schema_order() -> None:
    store = GuardStore()
    result, _line, _logged = _run(
        "update_subtask",
        {"plan_id": 1, "subtask_id": 2, "status": 3},
        store,
    )
    assert result.output == "Trường plan_id sai kiểu."
    assert store.calls == []


def test_subtasks_not_list() -> None:
    store = GuardStore()
    result, _line, _logged = _run(
        "create_plan",
        {"goal": "Học", "subtasks": ("Một",)},
        store,
    )
    assert result.output == "Trường subtasks sai kiểu."
    assert store.calls == []


@pytest.mark.parametrize(
    ("name", "tool_input", "output"),
    [
        ("create_plan", {"goal": None}, "Trường goal sai kiểu."),
        ("create_plan", {"goal": "Học", "subtasks": None}, "Trường subtasks sai kiểu."),
        ("get_plans", {"keyword": None}, "Trường keyword sai kiểu."),
    ],
)
def test_null_is_wrong_type(name: str, tool_input: dict, output: str) -> None:
    store = GuardStore()
    result, _line, _logged = _run(name, tool_input, store)
    assert result.output == output
    assert store.calls == []


@pytest.mark.parametrize("tool_input", [True, False])
def test_bool_input_is_not_object(tool_input: bool) -> None:
    store = GuardStore()
    result, _line, logged = _run("create_plan", tool_input, store)
    assert result.output == _NOT_OBJECT
    assert logged["error_type"] == "invalid_input"
    assert store.calls == []


def test_empty_keyword_lists_all() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Học tiếng Nhật", store=store))
    asyncio.run(create_plan("Nấu cơm", store=store))
    direct = asyncio.run(get_plans(keyword="", store=store))
    listed = asyncio.run(get_plans(store=store))
    result, _line, logged = _run("get_plans", {"keyword": ""}, store)
    assert result.success is True
    assert result.output == direct.output == listed.output
    assert logged["input"] == {"keyword": ""}


def test_whitespace_goal_keeps_domain_sentence() -> None:
    store = GuardStore()
    result, _line, logged = _run("create_plan", {"goal": " \t "}, store)
    assert result.output == _EMPTY_GOAL
    assert logged["error_type"] == "domain"
    assert store.calls == []


@pytest.mark.parametrize("status", ["DONE", "Skipped", "bỏ qua"])
def test_status_words_keep_domain_sentence(status: str) -> None:
    store = MemoryPlanStore()
    created = json.loads(asyncio.run(create_plan("Học", ["Một"], store=store)).output)
    result, _line, logged = _run(
        "update_subtask",
        {
            "plan_id": created["id"],
            "subtask_id": created["subtasks"][0]["id"],
            "status": status,
        },
        store,
    )
    assert result.output == _BAD_STATUS_WORD
    assert logged["error_type"] == "domain"


def test_empty_note_reaches_tool() -> None:
    store = MemoryPlanStore()
    created = json.loads(asyncio.run(create_plan("Học", ["Một"], store=store)).output)
    payload = {
        "plan_id": created["id"],
        "subtask_id": created["subtasks"][0]["id"],
        "note": "",
    }
    result, _line, logged = _run("set_subtask_note", payload, store)
    assert result.success is True
    assert logged["error_type"] is None
    assert json.loads(result.output)["subtasks"][0]["note"] is None


def test_keyword_filters_newest_first_and_two_subtasks() -> None:
    store = MemoryPlanStore()
    asyncio.run(create_plan("Nấu cơm", store=store))
    created, _line, logged = _run(
        "create_plan",
        {"goal": "Học tiếng Nhật", "subtasks": ["Hiragana", "Katakana"]},
        store,
    )
    assert created.success is True
    assert logged["input"] == {"goal": "Học tiếng Nhật", "subtasks": ["Hiragana", "Katakana"]}
    assert logged["error_type"] is None
    assert logged["detail"] is None
    assert [item["title"] for item in json.loads(created.output)["subtasks"]] == [
        "Hiragana",
        "Katakana",
    ]
    asyncio.run(create_plan("Đọc tiếng Anh", store=store))
    direct = asyncio.run(get_plans(keyword="tiếng", store=store))
    listed, _line, logged = _run("get_plans", {"keyword": "tiếng"}, store)
    assert listed.success is True
    assert listed.output == direct.output
    assert logged["error_type"] is None
    assert logged["detail"] is None
    assert [item["goal"] for item in json.loads(listed.output)["plans"]] == [
        "Đọc tiếng Anh",
        "Học tiếng Nhật",
    ]


def test_unexpected_calls_store_once_and_hides_url() -> None:
    class HttpStore(MemoryPlanStore):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def list_newest_first(self) -> tuple[Plan, ...]:
            self.calls += 1
            raise RuntimeError("http://127.0.0.1/secret")

    store = HttpStore()
    result, line, logged = _run("get_plans", {}, store)
    assert store.calls == 1
    assert result.output == _UNEXPECTED
    assert "http" not in result.output
    assert "http" not in line
    assert logged["error_type"] == "unexpected"
    assert logged["detail"] == "RuntimeError"


@pytest.mark.parametrize(
    "error",
    [SystemExit(), asyncio.CancelledError()],
    ids=["system_exit", "cancelled"],
)
def test_base_exception_escapes_without_log(error: BaseException) -> None:
    store = BoomStore(error, "list_newest_first")
    lines: list[str] = []
    with pytest.raises(type(error)):
        asyncio.run(execute_tool("get_plans", {}, store=store, log=lines.append))
    assert lines == []


def test_log_input_matches_sent_object() -> None:
    store = MemoryPlanStore()
    payload = {"goal": "Học tiếng Nhật", "subtasks": ["Hiragana", "Katakana"]}
    result, _line, logged = _run("create_plan", payload, store)
    assert result.success is True
    assert logged["input"] == payload
    assert logged["error_type"] is None
    assert logged["detail"] is None


def test_schema_required_drives_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        TOOL_DEFINITIONS["get_plans"]["input_schema"],
        "required",
        ["keyword"],
    )
    store = GuardStore()
    result, _line, logged = _run("get_plans", {}, store)
    assert result.output == "Đầu vào thiếu trường keyword."
    assert logged["error_type"] == "invalid_input"
    assert store.calls == []


def test_broken_catalog_is_unexpected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(TOOL_DEFINITIONS["get_plans"], "input_schema", "hỏng")
    store = GuardStore()
    result, _line, logged = _run("get_plans", {}, store)
    assert result.output == _UNEXPECTED
    assert logged["error_type"] == "unexpected"
    assert store.calls == []
