"""Runner nhận mapping và client giả. Không đọc khóa thật, không dựng AnthropicModel."""

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from core.llm import ModelResponse
from evals.runner import run_suite
from tests.test_eval_run import last_socket_calls, run_offline

_DAY = date(2026, 1, 2)
_MESSAGE = "Thiếu JARVIS_EVAL_ANTHROPIC_KEY."


class FakeClient:
    """Đếm lời gọi. Có thể ném giữa bộ."""

    model = "claude-haiku-5-5"

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.calls = 0
        self.api_keys: list[str] = []

    async def complete(self, request: object, *, api_key: str, timeout: float) -> ModelResponse:
        del request, timeout
        self.api_keys.append(api_key)
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ModelResponse(
            text="Mình nghe.",
            tool_requests=(),
            stop_reason="end_turn",
            input_tokens=1,
            output_tokens=1,
            model=self.model,
        )


@pytest.fixture(autouse=True)
def _offline_asyncio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evals.runner.asyncio.run", run_offline)


def _cases(directory: Path, broken: bool = False) -> tuple[Path, Path]:
    case_dir = directory / "cases"
    data_dir = directory / "datasets"
    case_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    payload: object = {"cases_version": 1, "cases": []} if not broken else {"cases_version": "no"}
    if not broken:
        payload = {
            "cases_version": 1,
            "cases": [
                {
                    "id": "c1",
                    "group": "chỉ kể việc",
                    "user_message": "kể",
                    "dataset": "",
                    "expectation": {"kind": "no_tool"},
                }
            ],
        }
    path = case_dir / "v1.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, data_dir


def _results_names() -> list[str]:
    directory = Path("evals/results")
    if not directory.exists():
        return []
    return sorted(item.name for item in directory.iterdir())


def _assert_no_socket() -> None:
    assert last_socket_calls() == 0


def test_runner_rejects_missing_empty_and_whitespace_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Khóa thiếu, rỗng, hoặc chỉ khoảng trắng thì dừng, mã 2, không gọi client, không ghi file."""

    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    client = FakeClient()
    for env in ({}, {"JARVIS_EVAL_ANTHROPIC_KEY": ""}, {"JARVIS_EVAL_ANTHROPIC_KEY": " \n\t "}):
        code = run_suite(env, client, out, _DAY, cases, datasets)
        assert code == 2
        captured = capsys.readouterr()
        assert captured.err.strip() == _MESSAGE
        assert captured.err.count("\n") == 1
    assert client.calls == 0
    assert list(out.iterdir()) == []
    _assert_no_socket()


def test_runner_keyboard_interrupt_writes_no_file(tmp_path: Path) -> None:
    """KeyboardInterrupt giữa bộ thì mã 130 và không có file."""

    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    client = FakeClient(error=KeyboardInterrupt())
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, client, out, _DAY, cases, datasets)
    assert code == 130
    assert list(out.iterdir()) == []
    _assert_no_socket()


def test_runner_cancelled_error_writes_no_file(tmp_path: Path) -> None:
    """CancelledError giữa bộ thì mã 130 và không có file."""

    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    client = FakeClient(error=asyncio.CancelledError())
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, client, out, _DAY, cases, datasets)
    assert code == 130
    assert list(out.iterdir()) == []
    _assert_no_socket()


def test_runner_full_run_writes_one_file(tmp_path: Path) -> None:
    """Bộ nhỏ chạy đủ thì đúng một file trong thư mục ra."""

    cases, datasets = _cases(tmp_path / "in")
    client = FakeClient()
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, client, tmp_path, _DAY, cases, datasets)
    files = [path for path in tmp_path.iterdir() if path.is_file()]
    assert code == 0
    assert len(files) == 1
    assert client.calls == 3
    _assert_no_socket()


def test_runner_leaves_evals_results_unchanged(tmp_path: Path) -> None:
    """Chạy bộ với tmp_path không thêm file trong evals/results."""

    before = _results_names()
    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, FakeClient(), out, _DAY, cases, datasets)
    assert code == 0
    assert _results_names() == before
    _assert_no_socket()


def test_runner_bad_format_writes_no_file(tmp_path: Path) -> None:
    """Sai định dạng bộ câu thì mã 2 và không ghi file."""

    cases, datasets = _cases(tmp_path / "in", broken=True)
    out = tmp_path / "out"
    out.mkdir()
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, FakeClient(), out, _DAY, cases, datasets)
    assert code == 2
    assert list(out.iterdir()) == []
    _assert_no_socket()


def test_runner_stdout_reports_fr013(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Stdout có tỉ lệ câu, luật, nhóm, cap_stops, run_errors, và hai tổng token."""

    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, FakeClient(), out, _DAY, cases, datasets)
    assert code == 0
    text = capsys.readouterr().out
    assert "input_tokens=" in text
    assert "output_tokens=" in text
    assert "case c1 " in text
    assert "run_errors=" in text
    assert "cap_stops=" in text
    assert "rule tool " in text
    assert "group chỉ kể việc " in text
    _assert_no_socket()


def test_runner_strips_surrounding_whitespace_from_key(tmp_path: Path) -> None:
    """Khóa có khoảng trắng hai đầu thì mọi lần client nhận khóa đã strip và ghi đúng một file."""

    cases, datasets = _cases(tmp_path / "in")
    client = FakeClient()
    code = run_suite(
        {"JARVIS_EVAL_ANTHROPIC_KEY": "  sk-test-key \n"},
        client,
        tmp_path,
        _DAY,
        cases,
        datasets,
    )
    files = [path for path in tmp_path.iterdir() if path.is_file()]
    assert code == 0
    assert len(files) == 1
    assert client.calls > 0
    assert client.api_keys == ["sk-test-key"] * client.calls
    _assert_no_socket()


def test_runner_one_case_prints_one_stderr_progress_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bộ một câu thì stderr đúng một dòng tiến độ, bằng mã kind thật, không chứa câu trả lời."""

    cases, datasets = _cases(tmp_path / "in")
    out = tmp_path / "out"
    out.mkdir()
    code = run_suite({"JARVIS_EVAL_ANTHROPIC_KEY": "k"}, FakeClient(), out, _DAY, cases, datasets)
    captured = capsys.readouterr()
    assert code == 0
    written = [path for path in out.iterdir() if path.is_file()]
    assert len(written) == 1
    body = json.loads(written[0].read_text(encoding="utf-8"))
    kinds = " ".join(str(item["kind"]) for item in body["runs"])
    assert captured.err.splitlines() == [f"[1/1] c1 {kinds}"]
    assert "Mình nghe." not in captured.err
    _assert_no_socket()


def test_runner_defaults_to_v1_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Không truyền đường dẫn thì runner đọc evals/cases/v1.json."""

    import sys
    import types
    from pathlib import Path

    from evals import runner

    seen: dict[str, object] = {}

    def fake(*args: object, **kwargs: object) -> int:
        del kwargs
        seen["path"] = args[4]
        return 0

    module = types.ModuleType("clients.anthropic_model")
    module.AnthropicModel = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clients.anthropic_model", module)
    monkeypatch.setattr(runner, "run_suite", fake)
    monkeypatch.setattr(runner.sys, "argv", ["runner"])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 0
    assert seen["path"] == Path("evals/cases/v1.json")


def test_runner_reads_case_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Đường dẫn trên lệnh là file bộ câu."""

    import sys
    import types

    from evals import runner

    seen: dict[str, object] = {}

    def fake(*args: object, **kwargs: object) -> int:
        del kwargs
        seen["path"] = args[4]
        return 0

    module = types.ModuleType("clients.anthropic_model")
    module.AnthropicModel = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clients.anthropic_model", module)
    monkeypatch.setattr(runner, "run_suite", fake)
    monkeypatch.setattr(runner.sys, "argv", ["runner", "evals/cases/v2.json"])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 0
    assert str(seen["path"]).replace("\\", "/") == "evals/cases/v2.json"
