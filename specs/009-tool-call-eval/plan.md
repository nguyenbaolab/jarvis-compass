# Implementation Plan: Bộ đánh giá gọi tool của một lượt

**Branch**: `009-tool-call-eval` | **Date**: 2026-10-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-tool-call-eval/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Một bộ đánh giá chạy ngoài Worker, gọi `run_turn` với client được truyền vào và `MemoryPlanStore` có sẵn. Phần thuần nằm trong `evals/`. Đúng một file `evals/runner.py` dựng `AnthropicModel`, đọc `JARVIS_EVAL_ANTHROPIC_KEY`, và bắt Ctrl+C. Bộ câu v1 để trống. Không sửa `src/`. Không thêm dependency.

Đối chiếu lựa chọn nằm ở [research.md](./research.md). Cách nhận log nằm ở [contracts/scoring.md](./contracts/scoring.md).

## Đã thấy

Import test, trích nguyên dòng:

```8:12:tests/test_tool_router.py
from core.plans import Plan, PlanDomainError, Subtask
from tests.fakes.memory_plan_store import MemoryPlanStore
from tools.plan_tools import create_plan, get_plans
from tools.tool_definitions import DEFINITIONS_VERSION, TOOL_DEFINITIONS
```

```12:12:tests/test_llm_turn.py
from turns.llm_turn import run_turn
```

`pyproject.toml:19-21`: `pythonpath = ["src"]`, `testpaths = ["tests"]`. Pytest còn đưa gốc repo vào `sys.path`, nên `tests.fakes` import được. `uv run python -m` từ gốc repo cũng đưa gốc vào `sys.path` cho gói `evals` và `tests`, nhưng không đưa `src`. Lệnh đã chốt, sau khi thử module tạm, là đặt `PYTHONPATH=src` rồi `uv run python -m evals.runner`. Output thử là `OK`, exit 0. Chi tiết ở [contracts/runner.md](./contracts/runner.md).

`git diff --exit-code -- src tests/fakes` lúc lập plan trả mã 0.

`docs/ARCHITECTURE.md:33` nói package ở gốc làm Worker `ModuleNotFoundError` khi deploy, nên package đang nằm trong `src/`. `evals/` vẫn ở gốc vì ràng buộc đã duyệt, và vì `src/` không import nó. Worker không bundle thứ entry không import.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Không thêm. `json`, `unicodedata`, `uuid`, `asyncio`, `socket` là thư viện chuẩn. `anthropic` đã có và chỉ được import trong `src/clients/anthropic_model.py`. Eval không import `anthropic` và không import `pydantic`.

**Storage**: File UTF-8 JSON trong `evals/cases/`, `evals/datasets/`, `evals/results/`. Không đổi DB. Kho mỗi lần chạy là `MemoryPlanStore`.

**Testing**: `uv run pytest` với client giả. Ca bịt `socket.socket`. Không mở mạng. Không sửa file test cũ. Lệnh ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython trên máy người giữ cho lệnh tay và pytest. Không đưa `evals/` vào Worker.

**Project Type**: Bộ đánh giá dòng lệnh, ngoài service.

**Performance Goals**: Không thêm ngân sách. Một lượt vẫn là ngân sách 20 giây của `run_turn`. Ba lần mỗi câu là 150 lượt cho bộ khoảng 50 câu. Chi phí nêu trong spec là bối cảnh lệnh tay, không phải ca pytest.

**Constraints**: Ràng buộc đã duyệt trong lệnh plan. Nguyên tắc I đến VIII. D-014, D-015, D-016. Không sửa `src/`. Không sửa `tests/fakes/memory_plan_store.py`. Không sửa `docs/PRODUCT.md`. Không hội thoại nhiều lượt. Không dùng mô hình để chấm.

**Scale/Scope**: Một bộ câu phiên bản 1, khoảng 50 câu, mười nhóm. Mỗi câu ba lần. File kết quả một lần chạy cả bộ.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Eval không tạo tên mới. Luật tự xưng chỉ đọc câu trả lời. |
| II. Worker không giữ trạng thái | Đạt | Eval không phải Worker và không lưu hội thoại giữa các request. |
| III. Database qua PostgREST | Đạt | Không đụng DB. Kho là bản trong bộ nhớ đã có. |
| IV. Gọi LLM qua lớp trung gian | Đạt | Mọi lần gọi mô hình của phần thuần đi qua `run_turn` và `ModelClient`. SDK không vào `evals/`. Khóa do runner truyền vào `run_turn`. Lượt và adapter không đọc môi trường, đúng câu nguyên tắc IV. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi kế hoạch ra kênh khác. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Eval không phải lời gọi từ desktop. Không lấy số 3 giây. |
| VIII. Unit test bắt buộc | Đạt | File test mới trong `tests/`. Mỗi luật có ca đạt và ca trượt. |
| Quy ước: config chỉ đọc qua `src/config/settings.py` | Đã duyệt ngoại lệ | Câu này không ghi phạm vi. Người duyệt đã chấp nhận ngoại lệ version `1.2.0` và D-017 đúng chữ đề xuất dưới đây. Sửa `.specify/memory/constitution.md` và `docs/DECISIONS.md` ở implement, không sửa ở bước plan. |

Không có cổng nguyên tắc I đến VIII bị lệch. Ngoại lệ quy ước đã duyệt, file constitution và DECISIONS chưa sửa.

### Sau Phase 1

Đã đối chiếu [research.md](./research.md), [data-model.md](./data-model.md), [contracts/scoring.md](./contracts/scoring.md), [contracts/case-file.md](./contracts/case-file.md), [contracts/result-file.md](./contracts/result-file.md), [contracts/runner.md](./contracts/runner.md), và [quickstart.md](./quickstart.md).

- Phần thuần không import `clients`, `anthropic`, `pydantic`, và không đọc `os.environ`.
- Chỉ `evals/runner.py` import `clients.anthropic_model` và đọc một biến môi trường.
- `src/` không có trong phạm vi file, nên không có dòng mới nào import `evals`.
- Cổng quy ước config đã được duyệt bằng ngoại lệ `1.2.0` và D-017. File constitution và `docs/DECISIONS.md` sửa ở implement. Các cổng I đến VIII vẫn đạt.

## Đề xuất constitution và D-017

**Đã duyệt.** Version constitution `1.2.0` và D-017 đúng chữ dưới đây. Sửa `.specify/memory/constitution.md` và `docs/DECISIONS.md` ở implement, không sửa ở bước plan.

Nguyên văn câu đang có, constitution mục Quy ước mã nguồn:

> Type hints bắt buộc cho mọi function public; Pydantic cho request, response và schema DB; config chỉ đọc qua `src/config/settings.py`; tool dùng mẫu `ToolResult` và `ToolError`; comment tiếng Việt.

Câu không nói phạm vi là `src/` hay cả repo. `src/config/settings.py:41-46` đọc `TELEGRAM_BOT_TOKEN` bằng `os.getenv`. File đó không có `JARVIS_EVAL_ANTHROPIC_KEY`. Thêm biến vào đó là sửa `src/`, bị cấm.

Nguyên tắc IV, nguyên văn:

> Mọi lời gọi LLM đi qua cổng trung lập trong `src/core/llm.py`. SDK của nhà cung cấp chỉ được import trong adapter nằm ngoài `src/core`; model và endpoint đặt trong adapter (D-004, D-015). API key do người gọi truyền vào từ cấu hình runtime; code của lượt và adapter không đọc biến môi trường.

Runner là người gọi. Nó đọc biến rồi truyền vào `run_turn`. Nguyên tắc IV không bị lệch. Câu quy ước thì lệch nếu hiểu nó áp cả repo.

Đã duyệt thêm vào mục Quy ước mã nguồn, version `1.1.0` thành `1.2.0` khi implement sửa file:

> Ngoại lệ: file `evals/runner.py` được đọc biến `JARVIS_EVAL_ANTHROPIC_KEY` từ môi trường tiến trình của lệnh chạy tay, rồi truyền giá trị đó vào lượt. Không file nào khác trong `evals/` được đọc biến môi trường. `src/` không đọc biến này.

Đã duyệt mục mới `docs/DECISIONS.md`. Ghi vào file đó ở implement. Không ghi trong bước plan.

**D-017 — Runner eval đọc một biến môi trường**

**Status:** Đã duyệt, ghi vào `docs/DECISIONS.md` ở implement

**Bối cảnh:** Quy ước mã nguồn nói config chỉ đọc qua `src/config/settings.py` và không ghi phạm vi. Lệnh eval chạy tay cần khóa. Nguyên tắc IV cấm lượt và adapter đọc môi trường. Ràng buộc đã duyệt: không sửa `src/`, và chỉ `evals/runner.py` đọc `JARVIS_EVAL_ANTHROPIC_KEY`.

**Quyết định:** Ngoại lệ nằm trong constitution, đúng câu đề xuất ở plan này. Chỉ ghi trong AGENTS.md là không đủ.

**Phương án đã bỏ:** thêm khóa vào `src/config/settings.py`. Để runner đọc môi trường mà không sửa constitution.

Chữ đã duyệt, không đổi. Phần thuần và test không đọc biến môi trường.

## FR-012 đối chiếu code

Nguyên văn toàn bộ `_finish`, `src/turns/llm_turn.py:111-120`:

```python
def _finish(response: ModelResponse, done: int) -> str | None:
    """Câu trả về khi không còn chạy tool. None nghĩa là còn một vòng tool."""

    if response.stop_reason == "end_turn":
        return response.text
    if response.stop_reason == "tool_use" and done >= _MAX_ROUNDS:
        return _CAP
    if response.stop_reason == "tool_use" and response.tool_requests:
        return None
    return _MODEL_ERROR
```

Mọi chỗ `run_turn` trả về, cùng file:

```python
        if remaining <= 0:
            return _MODEL_ERROR
```

dòng 142-143, trước `complete`, không gọi `_model_log`.

```python
            return _MODEL_ERROR
```

dòng 163, sau `_model_log` với `stop_reason=None` và `error_type=_error_type(error)`.

```python
        outcome = _finish(response, len(done))
        if outcome is not None:
            return outcome
```

dòng 173-175, sau `_model_log` với `error_type=None` và `stop_reason=response.stop_reason`.

```python
        if isinstance(tool_results, str):
            return tool_results
```

dòng 182-183. `_run_tools` trả chuỗi khi hết ngân sách giữa các tool, `llm_turn.py:93-94`, không thêm dòng tám khóa. Dòng 184 `done.append` chỉ chạy khi tool của vòng đó chạy xong.

`_MAX_ROUNDS` là `3`, dòng 22. Nhánh `end_turn` là nhánh duy nhất trả `response.text`. Tập `stop_reason` kết thúc hợp lệ, liệt kê từ các nhánh đó, là đúng một giá trị: `end_turn`. Nhánh `tool_use` và `done >= 3` là hết lượt tool, định nghĩa riêng bên dưới, không đưa `tool_use` vào tập này. Nhánh `tool_use` còn `tool_requests` trả `None` và vòng lặp tiếp. Mọi `stop_reason` khác, gồm `max_tokens`, rơi vào `return _MODEL_ERROR` ở cuối `_finish`.

Không so câu trả lời. Phân loại theo thứ tự này, một lần một mã trong file kết quả:

| Thứ tự | Điều kiện | Mã | Chấm luật |
|---|---|---|---|
| 1 | Ném `MissingKeyError` | `missing_key` | Không |
| 2 | Không có dòng tám khóa | `no_model_log` | Không |
| 3 | Dòng log cuối là dòng bảy khóa | `ended_on_tool_log` | Không |
| 4 | Dòng cuối là dòng tám khóa, `error_type` khác `null` | `model_error` | Không |
| 5 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `tool_use`, và trước dòng đó đã có đúng ba vòng tool | hết lượt tool, không phải lỗi chạy | Có |
| 6 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `end_turn` | kết thúc bình thường | Có |
| 7 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` ngoài tập | `bad_stop_reason` | Không |

Năm mã lỗi chạy là `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`. Hết ngân sách trước `complete` là `no_model_log`. Hết ngân sách sau ít nhất một tool của vòng đang chạy là `ended_on_tool_log`. `max_tokens` là `bad_stop_reason`.

Số vòng không có trường riêng. Một vòng là dòng tám khóa có `stop_reason` bằng `tool_use` và có ít nhất một dòng bảy khóa trước dòng tám khóa kế tiếp. Dòng `tool_use` không có dòng bảy khóa theo sau không cộng vòng. Chi tiết ở [contracts/scoring.md](./contracts/scoring.md).

## Project Structure

### Documentation (this feature)

```text
specs/009-tool-call-eval/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── scoring.md
│   ├── case-file.md
│   ├── result-file.md
│   └── runner.md
└── tasks.md             # /speckit-tasks, không tạo ở bước này
```

### Source Code (repository root)

```text
evals/
├── __init__.py          # docstring, không import
├── model.py             # StrEnum nhóm, dataclass câu và kỳ vọng
├── load.py              # đọc JSON, NFC, từ chối bộ sai
├── store.py             # dựng MemoryPlanStore từ bộ dữ liệu
├── turn.py              # một lần run_turn, và ba lần độc lập
├── score.py             # bảy luật
├── summary.py           # tỉ lệ, số hết lượt tool, token
├── redact.py            # giấu khóa không rỗng
├── result.py            # ghi file mới
├── runner.py            # main đọc môi trường và dựng client
├── cases/v1.json        # task riêng, chờ nguyên văn, plan không điền câu
├── datasets/            # file JSON người giữ đưa kèm bộ câu
└── results/             # file kết quả do lệnh tay ghi

tests/
├── test_eval_load.py
├── test_eval_store.py
├── test_eval_score.py
├── test_eval_run.py
├── test_eval_result.py
└── test_eval_runner.py
```

**Structure Decision**: `evals/` ở gốc, ngoài `src/`, vì ràng buộc đã duyệt và vì Worker không được import gói này. Module thuần nhận `ModelClient`. Trong `runner.py`, hàm kiểm khóa, vòng chạy cả bộ, và xử lý `KeyboardInterrupt` nhận một mapping môi trường và một client. Chỉ `main` đọc `os.environ` và dựng `AnthropicModel`. Test của các hàm đó nằm ở `tests/test_eval_runner.py`.

## Chữ ký dùng để dựng kho

`SubtaskStatus` và `Subtask`, `src/core/plans.py:18-33`:

```python
class SubtaskStatus(StrEnum):
    """Trạng thái việc con: pending, done, hoặc skipped."""

    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Subtask:
    """Một việc con. Danh tính giữ nguyên khi trạng thái hoặc ghi chú đổi."""

    id: str
    title: str
    status: SubtaskStatus
    note: str | None
```

`new_subtask`, dòng 68, chỉ tạo `PENDING` và `note=None`. `normalize_new_plan(goal, None)`, dòng 84, trả mục tiêu đã NFC. `normalize_subtask_note`, dòng 189, NFC và đổi rỗng thành `None`. `MemoryPlanStore.add`, `tests/fakes/memory_plan_store.py:15-16`, giữ id và status của việc con, tự cấp id kế hoạch.

Cách dựng nằm ở [contracts/case-file.md](./contracts/case-file.md). Không viết kho thứ hai.

## Pydantic

Không dùng cho file bộ câu. Constitution giao Pydantic cho request, response, và schema DB. Ba chỗ đó không phải file eval. Parse bằng `json` và dataclass. Không thêm dependency.

## `scripts/check.ps1`

Dùng lại `Invoke-GrepCheck`. Hàm này gọi `git grep -n --untracked -E`, `scripts/check.ps1:152`. Thêm tham số tùy chọn `-Allow`, một mẫu. Sau `git grep`, lấy phần mã nguồn sau tiền tố `đường-dẫn:số-dòng:`, rồi bỏ dòng nào phần đó khớp `-Allow` bằng `-notmatch`. Sáu hàng hiện có không truyền `-Allow`, nên hành vi các hàng đó không đổi.

`-notmatch` trên cả dòng output của `git grep` không bỏ được dòng hợp lệ: dòng đó bắt đầu bằng đường dẫn, còn mẫu `-Allow` neo `^` vào chữ `from` hoặc `import`. Đã thử. Vì vậy implement áp `-notmatch` lên phần mã nguồn, không lên cả dòng output.

Ba thay đổi:

1. Hàng `SDK imports` thêm pathspec `evals`. Mẫu giữ nguyên, dòng 404-406: `^\s*(from|import)\s+anthropic\b` và `^\s*from\s+\.+anthropic\b`. Pathspec thành `src`, `:!src/clients/anthropic_model.py`, `evals`. Không truyền `-Allow`.
2. Hàng mới `Eval tests imports`, pathspec `evals`. Mẫu cấm `^\s*(from|import)\s+tests\b`. Mẫu `-Allow` là `^\s*(from|import)\s+tests\.fakes\.memory_plan_store(\s|$)`.
3. Hàng mới `Eval env reads`, pathspec `evals` và `:!evals/runner.py`, hai mẫu đang có của hàng Env reads, dòng 408-409: `\bos\.(getenv|environ)\b` và `^\s*from\s+os\s+import\s+.*\b(getenv|environ)\b`. Không truyền `-Allow`.

File tạm đã xóa sau khi thử. Hàng tests: `git grep` rồi `-notmatch` trên phần mã nguồn.

| Dòng | Sau lọc |
|---|---|
| `from tests.helpers import MemoryPlanStore` | Còn |
| `from tests.fakes.memory_plan_store_extra import MemoryPlanStore` | Còn |
| `from tests.fakes.memory_plan_store.extra import MemoryPlanStore` | Còn |
| `import tests` | Còn |
| `from tests.fakes.memory_plan_store import MemoryPlanStore` | Bỏ |
| `import tests.fakes.memory_plan_store` | Bỏ |

Hai hàng SDK và hai hàng env giữ kết quả đã thử ở bước plan trước. Implement thêm dòng in bảng cuối và nhánh `$anyFail` theo đúng kiểu sáu hàng hiện có.

## Docs ở B10

- `AGENTS.md`: thêm lệnh ở [contracts/runner.md](./contracts/runner.md), kèm "chưa chạy thử" cho tới khi chạy thật. Không ghi giá trị khóa.
- `docs/ARCHITECTURE.md`: thêm `evals/` ở mục module. Sửa câu "toàn bộ package nằm trong `src/`" để nói `evals/` nằm ngoài bundle Worker và `src/` không import nó.
- `docs/DECISIONS.md`: thêm D-017 đúng chữ đã duyệt. Làm ở implement.
- Archify, D-016 nguyên văn điều kiện cập nhật: "thêm gói hoặc ranh giới mới trong `src/`, nối hai cụm code chưa nối, thêm composition root". `evals/` không nằm trong `src/`, không nối hai cụm `src/` chưa nối, không phải composition root. Diagram trong `docs/architecture/` không sửa.

## Phạm vi file

Danh sách này là danh sách duy nhất được phép. `allowed-files.txt` tạo sau `/speckit-tasks`, mỗi dòng một đường dẫn, cộng `specs/009-tool-call-eval/**`. Không dùng `*` ngoài hậu tố `/**` mà `check.ps1` đã hiểu.

```text
evals/__init__.py
evals/model.py
evals/load.py
evals/store.py
evals/turn.py
evals/score.py
evals/summary.py
evals/redact.py
evals/result.py
evals/runner.py
evals/cases/v1.json
evals/datasets/**
evals/results/**
tests/test_eval_load.py
tests/test_eval_store.py
tests/test_eval_score.py
tests/test_eval_run.py
tests/test_eval_result.py
tests/test_eval_runner.py
scripts/check.ps1
AGENTS.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
.specify/memory/constitution.md
specs/009-tool-call-eval/**
```

`docs/DECISIONS.md` và `.specify/memory/constitution.md` sửa ở implement, đúng chữ đã duyệt. `evals/cases/v1.json` và file trong `evals/datasets/` chỉ có nội dung khi người giữ đưa nguyên văn. Task riêng của `/speckit-tasks` phải là "đưa bộ câu v1 nguyên văn" và phải chờ. Không bịa câu trong task khác.

Không có `src/`, không có `tests/fakes/`, không có file test cũ, không có `docs/PRODUCT.md`, không có `docs/architecture/`.

## Task bắt buộc ở bước sau

`/speckit-tasks` phải có một task, tách riêng, tên việc là đưa bộ câu v1 nguyên văn. Task đó không có sẵn chữ câu. Nó chờ người giữ. Các task khác không điền 50 câu.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Runner đọc `JARVIS_EVAL_ANTHROPIC_KEY` trong khi quy ước nói config chỉ qua `src/config/settings.py` | Ràng buộc đã duyệt: không sửa `src/`, và chỉ một file runner đọc biến này. Nguyên tắc IV vẫn giữ vì lượt và adapter không đọc môi trường. Ngoại lệ `1.2.0` và D-017 đã duyệt. | Sửa `settings.py` là sửa `src/`. Chỉ ghi ngoại lệ trong AGENTS.md thì không đủ, vì người duyệt yêu cầu ngoại lệ nằm trong constitution. |
