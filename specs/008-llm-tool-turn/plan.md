# Implementation Plan: Lượt trả lời có gọi mô hình

**Branch**: `008-llm-tool-turn` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-llm-tool-turn/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Một lượt nhận tin mới, lịch sử văn bản, kho, khóa, một cổng mô hình, và một hàm log. Cổng ở `src/core/llm.py` chỉ dùng thư viện chuẩn. Adapter Anthropic ở `src/clients/` dịch sang SDK và đổi exception của SDK thành lỗi phía mô hình, chỉ giữ tên lớp. Vòng lặp gọi `execute_tool` nên đứng ở `src/turns/llm_turn.py`: `src/core` không được import `tools`. Prompt là hằng trong `src/core/system_prompt.py`. Danh sách tool là `TOOL_DEFINITIONS` sẵn có, không chép. Ngân sách 20 giây đo bằng `_now` của module lượt. `max_tokens` là 2048.

Đối chiếu lựa chọn nằm ở [research.md](./research.md).

## Đã thấy

- `src/core/llm.py` hiện là một docstring. `execute_tool` là `async def` và nhận `log` keyword-only. `_now` của router gọi `time.monotonic()` và test bịt đúng hàm đó.
- `check.ps1` làm fail nếu `src/core` có import `fastapi`, `pydantic`, `tools`, hoặc `db`. D-011: tools import core; core không import tools hay db.
- `pyproject.toml` đã có `anthropic` trong `dependencies`. Không thêm dependency.
- `git grep ANTHROPIC_API_KEY -- src/config/settings.py` chỉ thấy dòng khai báo. `git grep` trên file Python chỉ thấy đúng dòng đó. Không file Python nào đọc hằng này. `TELEGRAM_BOT_TOKEN` giữ nguyên.
- D-002: một nhân vật JARVIS, không có tên thứ hai. D-004 đã ghi `claude-haiku-5-5` ở câu cập nhật 2026-10-18, nên không sửa D-004. B10 thêm D-015.
- SDK đã cài là `anthropic` 1.5.0. `AsyncAnthropic` nhận `api_key`, `timeout`, `max_retries` (mặc định 2). `messages.create` bắt buộc `max_tokens`, `messages`, `model`, và có `thinking`, `tools`, `system`. `StopReason` gồm `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`, `refusal`, `model_context_window_exceeded`. `thinking` tắt là `{"type": "disabled"}`.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `anthropic` đã có trong dependency chính. Không thêm thư viện. Không `pytest-asyncio`. Test async bằng `asyncio.run`.

**Storage**: Không lưu hội thoại. Không đổi lược đồ. Lượt nhận kho đã có và không dựng kho thật.

**Testing**: `uv run pytest`. Hai file test mới. Test lượt dùng client giả ở mức cổng. Test adapter bịt constructor SDK. Không mở mạng. Assertion test cũ không sửa. Cách chạy nằm ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython cho pytest, và module phải nằm dưới `src/` để Worker bundle được. Lát này không thêm route.

**Project Type**: Phần lượt gọi mô hình của web service. Không có endpoint mới.

**Performance Goals**: Cả lượt, gồm mọi lần gọi mô hình và mọi lần chạy tool, nằm trong 20 giây. Spike một lượt có một lần tool là 5 đến 7 giây. Không thử lại.

**Constraints**: Nguyên tắc I đến VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-002, D-011, D-012, D-014 trong [docs/DECISIONS.md](../../docs/DECISIONS.md). Không sửa `src/tools/tool_router.py`, `src/tools/tool_definitions.py`, `src/core/plans.py`. Không bịt `time.monotonic` toàn tiến trình. Không đọc `.env` thật hay `.dev.vars`. Khóa lấy từ đối số, không từ `os.getenv`.

**Scale/Scope**: Một cổng, một prompt, một vòng lặp, một adapter, hai file test, một dòng cấu hình bị xóa, một đoạn cập nhật kiến trúc.

## Các lựa chọn đã so

Bản đầy đủ ở [research.md](./research.md).

**a. Chỗ đặt.** Cổng và prompt ở `src/core`. Adapter ở `src/clients/anthropic_model.py`. Vòng lặp ở `src/turns/llm_turn.py`. Bảng import ở dưới.

**b. Đồng bộ.** `run_turn` và `complete` là `async def` vì `execute_tool` là `async def` và SDK có `AsyncAnthropic`.

**c. Ngân sách.** `_now` của `llm_turn` gọi `time.monotonic()`. Trước mỗi lần gọi mô hình và mỗi lần `execute_tool`, hết giờ thì không bắt đầu việc đó. Lần gọi mô hình đang chạy được giới hạn bằng `timeout` của SDK. Lần `execute_tool` đã bắt đầu không cắt được giữa chừng.

**d. `max_tokens`.** 2048, hằng của adapter. Đây là trần. Chỉ token sinh ra mới tính phí. `create_plan` tiếng Việt nhiều việc con có thể vượt 1024 và làm cả lượt ra câu lỗi. `stop_reason` khác `end_turn` và `tool_use` không chạy tool và không gọi mô hình thêm.

**e. Log.** Một hàm. Lượt truyền đúng hàm đó vào `execute_tool`. Dòng mô hình ghi khi lần gọi mô hình kết thúc, trước tool của phản hồi đó. Dòng thành công lấy `model` từ `ModelResponse`. Dòng lỗi của `complete` lấy `model` từ `client.model`. Hai loại dòng phân biệt bằng khóa `model` và khóa `tool`.

**f. Khóa.** Xóa dòng `ANTHROPIC_API_KEY` trong `settings.py`. Không đụng `TELEGRAM_BOT_TOKEN`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Prompt lấy tên và vai từ D-002: JARVIS, không tên thứ hai. |
| II. Worker không giữ trạng thái | Đạt | Lượt không lưu hội thoại. Khối tool chỉ sống trong lần gọi. |
| III. Database qua PostgREST | Đạt | Lượt không import `db` và không dựng kho. |
| IV. LLM qua lớp trung gian | Đạt | Mọi lời gọi của lượt đi qua Protocol trong `src/core/llm.py`. SDK không vào file đó. Khóa là đối số người gọi, cùng kiểu nguồn với `require_supabase`, không hardcode. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi kế hoạch ra kênh khác. |
| VII. Ngân sách độ trễ với jarvis-desktop | Đạt | Lát này không thêm lời gọi từ desktop. Ngân sách 20 giây là của lượt có mô hình, không lấy số 3 giây của nguyên tắc VII. |
| VIII. Unit test bắt buộc | Đạt | Hai file test mới. Lệnh nằm ở [quickstart.md](./quickstart.md). |

Không có cổng thất bại. Không có ràng buộc nào phải dừng.

### Sau Phase 1

Đã đối chiếu [research.md](./research.md), [data-model.md](./data-model.md), [contracts/model-port.md](./contracts/model-port.md), [contracts/llm-turn.md](./contracts/llm-turn.md), [contracts/anthropic-adapter.md](./contracts/anthropic-adapter.md), [contracts/system-prompt.md](./contracts/system-prompt.md), và [quickstart.md](./quickstart.md).

- `src/core/llm.py` và `src/core/system_prompt.py` không import `anthropic`, `tools`, `db`, `fastapi`, `pydantic`.
- `src/turns/llm_turn.py` import cổng, prompt, `execute_tool`, và catalog. Không import adapter, `db`, hay `settings`.
- `src/clients/anthropic_model.py` import SDK và cổng. Không import `turns` hay `tools`.
- Không có chiều import ngược. `execute_tool`, catalog, và `src/core/plans.py` không sửa.
- `anthropic` đã nằm trong dependency chính. Không thêm dòng dependency.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/008-llm-tool-turn/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── model-port.md
│   ├── llm-turn.md
│   ├── anthropic-adapter.md
│   └── system-prompt.md
└── tasks.md             # /speckit-tasks, không tạo ở bước này
```

### Source Code (repository root)

```text
src/core/
├── llm.py                       # sửa: thay docstring bằng kiểu cổng và Protocol
├── system_prompt.py             # tạo: SYSTEM_PROMPT và PROMPT_VERSION
└── plans.py                     # không sửa

src/turns/
├── __init__.py                  # tạo: docstring gói
└── llm_turn.py                  # tạo: run_turn, _now, ba câu

src/clients/
├── anthropic_model.py           # tạo: adapter AsyncAnthropic
└── telegram.py                  # không sửa

src/tools/
├── tool_router.py               # không sửa
└── tool_definitions.py          # không sửa

src/config/settings.py           # sửa: xóa dòng ANTHROPIC_API_KEY

tests/
├── test_llm_turn.py             # tạo
├── test_anthropic_model.py      # tạo
└── (các file test hiện có)      # không sửa assertion

docs/ARCHITECTURE.md             # sửa đoạn trạng thái, §2, §3, §6
```

**Structure Decision**: Vòng lặp không ở `src/core` vì nó phải gọi `execute_tool` trong khi luật import cấm core import `tools`. Không ở `src/tools` vì D-011 giữ tool là lớp mỏng và `execute_tool` là lối vào duy nhất, không phải chỗ sở hữu lượt. Không ở `src/clients` vì gói đó là kênh ra ngoài; adapter Anthropic mới thuộc gói đó. `src/turns/` nằm dưới `src/`, cùng cấp với entry, nên Worker bundle được khi có người import.

## Import mới

| File | Import | Luật cho phép |
|------|--------|----------------|
| `src/core/llm.py` | `dataclasses`, `typing` | Ràng buộc 1: cổng chỉ thư viện chuẩn. D-011: core không import tools hay db. `check.ps1` cấm `fastapi`, `pydantic`, `tools`, `db` trong `src/core`. |
| `src/core/system_prompt.py` | không import | Ràng buộc 4: hằng văn bản, không đọc file. D-002 chỉ lấy tên và vai để viết hằng. |
| `src/turns/llm_turn.py` | `core.llm`, `core.system_prompt`, `core.plans.PlanStore` | Chiều ngoài vào core, cùng hướng D-011 cho phép tools import core. |
| `src/turns/llm_turn.py` | `tools.tool_router.execute_tool`, `tools.tool_definitions`, `tools.base.ToolResult` | D-011 cấm core import tools, không cấm gói ngoài import tools. `check.ps1` không cấm import này. D-014: tool call đi qua `execute_tool`. |
| `src/clients/anthropic_model.py` | `anthropic`, `core.llm` | Ràng buộc 2: adapter ngoài core. FR-014. Nguyên tắc IV: SDK không nằm trong cổng. `anthropic` đã có trong dependency chính. |

Không thêm chiều nào khác. `core` không import `turns` hay `clients`. `clients` không import `turns` hay `tools`. `tools` không import `turns` hay `clients`. Không có vòng.

## Hành vi đã chốt

### Một hàm log

`run_turn` nhận một `log`. Khi người gọi không đưa, lượt dùng một hàm mặc định in một dòng. Đúng hàm đó, kể cả hàm mặc định, được truyền vào mọi `execute_tool` của lượt. Dòng mô hình ghi ngay khi lần gọi mô hình kết thúc, rồi mới chạy tool. Vì vậy một vòng có tool cho ra dòng mô hình trước, rồi từng dòng tool theo thứ tự chạy.

### Ngân sách

`_now` trong `src/turns/llm_turn.py` trả `time.monotonic()`. Mốc đầu lượt lấy một lần. Hết giờ khi `_now() - mốc > 20`. Test bịt `turns.llm_turn._now`, không bịt `time.monotonic`.

Trước mỗi `complete` và trước mỗi `execute_tool`, lượt đo lại. Hết giờ thì không bắt đầu việc đó, không gọi thêm, và trả `Chưa liên lạc được để trả lời lúc này.`

Lần gọi mô hình đang chạy: adapter mở client bằng `async with AsyncAnthropic(api_key=..., timeout=..., max_retries=0) as client:` rồi đóng kết nối khi hết khối. `timeout` là số giây còn lại. Hết timeout thì SDK ném lỗi; adapter đổi thành lỗi phía mô hình; lượt trả câu lỗi và không gọi thêm. Lượt không dùng `asyncio.wait_for`, vì hủy task bên trong sẽ thành `CancelledError`, và `CancelledError` phải đi tiếp chứ không thành câu lỗi ngân sách.

Lần `execute_tool` đã bắt đầu: không chặn được giữa chừng. Hàm này không có tham số timeout, và file router không được sửa. Lượt chờ nó trả về. Ghi của tool vào kho, nếu đã xảy ra, không hoàn lại. Sau khi nó trả về, lượt đo lại và không bắt đầu tool kế tiếp hay lần gọi mô hình kế tiếp nếu đã hết giờ.

### Đồng bộ

`run_turn` là `async def`. `execute_tool` đã là `async def`. Adapter `await` `AsyncAnthropic.messages.create` để không chặn vòng sự kiện trên Worker. Test gọi bằng `asyncio.run`. Không thêm `pytest-asyncio`.

### max_tokens và stop_reason

Adapter gửi `max_tokens=2048` và `thinking={"type": "disabled"}`. Không gửi `stream`. 2048 là trần. Chỉ token sinh ra mới tính phí. `create_plan` tiếng Việt nhiều việc con có thể vượt 1024 và làm cả lượt ra câu lỗi.

- `end_turn`: kết quả là văn bản của phản hồi, kể cả chuỗi rỗng. Không chạy tool.
- `tool_use` và có ít nhất một yêu cầu đủ id, tên, và object: một vòng, nếu còn trong 3 vòng.
- `max_tokens`, `stop_sequence`, `pause_turn`, `refusal`, `model_context_window_exceeded`, hoặc `stop_reason` trống: không chạy tool nào của phản hồi đó, kể cả khi có khối tool dở, không gọi mô hình thêm, trả câu lỗi phía mô hình. Dòng log của lần gọi đã kết thúc vẫn ghi `stop_reason` nhận được và `error_type` trống. `error_type` chỉ có giá trị khi `complete` ném exception.

Adapter chỉ đưa yêu cầu tool vào phản hồi cổng khi `stop_reason` là `tool_use` và khối có id, tên, cùng input là object. Khối không đủ thì không thành yêu cầu tool; exception của SDK khi phân tích khối thành `ModelError` với tên lớp SDK.

### Lịch sử

Đối số lịch sử chỉ là tin văn bản, vai `user` hoặc `assistant`. Lượt không sửa list người gọi đưa. Yêu cầu tool và kết quả tool chỉ nằm trong đối số của lần `complete` kế tiếp trong cùng lượt. Chúng không nằm trong giá trị trả về. Giá trị trả về là một chuỗi, hoặc lỗi thiếu khóa.

### Khóa và dependency

Thiếu khóa hoặc chuỗi rỗng: ném lỗi đúng câu `Thiếu ANTHROPIC_API_KEY.` trước mọi `complete`. Không đọc môi trường tiến trình. Chuỗi chỉ khoảng trắng được coi là đã có khóa.

`git grep` không thấy người đọc hằng `ANTHROPIC_API_KEY`. Xóa dòng đó trong `src/config/settings.py`. Giữ `TELEGRAM_BOT_TOKEN` và `_get_str`.

`anthropic` đã có trong `dependencies` của `pyproject.toml`. Không thêm dependency. Không sửa `pyproject.toml`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.

## Cách làm khi implement

Viết hai file test trước. Chạy và in output lần fail, rồi mới viết mã trong `src/` và sửa `docs/ARCHITECTURE.md`, `docs/PRODUCT.md`, `docs/DECISIONS.md`. Không sửa assertion của test cũ. Không sửa ba file bị cấm ở mục dưới. Không thêm dependency.

Năm ca sau là năm hàm test riêng trong `tests/test_llm_turn.py`: giới hạn 3 vòng, thiếu khóa hoặc khóa rỗng trước mọi lời gọi client, vượt ngân sách thì không gọi thêm, `CancelledError` đi tiếp, kết quả không chứa thông điệp lỗi.

`allowed-files.txt` không tạo ở bước plan. Tạo ngay sau `/speckit-tasks`, đúng các dòng ở mục dưới.

## File được tạo hoặc sửa

Danh sách này là nội dung `specs/008-llm-tool-turn/allowed-files.txt` ở bước tasks. Mỗi dòng một đường dẫn tương đối, dấu `/`, không có `*` ngoài dòng thư mục spec.

```text
src/core/llm.py
src/core/system_prompt.py
src/turns/__init__.py
src/turns/llm_turn.py
src/clients/anthropic_model.py
src/config/settings.py
tests/test_llm_turn.py
tests/test_anthropic_model.py
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/PRODUCT.md
specs/008-llm-tool-turn/**
```

Không đưa vào danh sách, và không sửa: `src/tools/tool_router.py`, `src/tools/tool_definitions.py`, `src/core/plans.py`, `src/app.py`, `src/clients/telegram.py`, `pyproject.toml`, `uv.lock`, `.env.example`, `docs/architecture/architecture.json`, `docs/architecture/architecture.html`, mọi file test đã có.

`docs/architecture/architecture.json` và `architecture.html` là đồ thị đã sinh, có một câu nói `settings.py` khai báo `ANTHROPIC_API_KEY`. Câu đó sẽ cũ sau khi xóa dòng. Lát này không sửa hai file đó. Nguồn kiến trúc được sửa là `docs/ARCHITECTURE.md`.

## Docs cần cập nhật khi implement

Chưa sửa ở bước plan.

`docs/ARCHITECTURE.md`, chỉ các chỗ sau:

- Đoạn trạng thái: giữ các câu hiện có về `/health`, `db.plan_store`, F04 đến F08, và `execute_tool`. Thêm rằng lượt mô hình nằm ở `src/turns/llm_turn.py`, gọi cổng `src/core/llm.py` rồi `execute_tool`. Route và Telegram chưa gọi lượt này. Khóa mô hình do người gọi đưa, không đọc từ `settings`.
- §2, dòng `src/core/`: `llm.py` là cổng trung lập, chỉ thư viện chuẩn. `system_prompt.py` là hằng prompt và `PROMPT_VERSION`.
- §2, thêm dòng `src/turns/`: vòng lặp của một lượt, gọi `execute_tool`, không import SDK.
- §2, dòng `src/clients/`: thêm adapter Anthropic bên cạnh Telegram. Adapter dịch cổng sang SDK.
- §3: mũi tên gọi mô hình trỏ `turns/llm_turn.py` qua cổng `core/llm.py`, rồi `execute_tool` khi phản hồi đòi tool. Không ghi tool calling bên trong `core/llm.py`.
- §6: thêm một câu rằng mỗi lần gọi mô hình đã kết thúc ghi một dòng JSON tám khóa qua cùng hàm log được truyền vào `execute_tool`. Không thêm thư viện log. Câu loguru chưa chốt giữ nguyên.

`docs/PRODUCT.md`, hàng F12: bỏ chữ OpenAI-compatible. Ghi cổng trung lập và adapter Anthropic. Không sửa dòng ước tính chi phí.

`docs/DECISIONS.md`: thêm D-015 vào cuối file. Không sửa D-010 đến D-014, trừ D-004 chỉ thêm một dòng, không xóa câu cũ. D-004 đã có câu cập nhật 2026-10-18 ghi `claude-haiku-5-5`. Thêm dòng `Cập nhật 2026-10-26:` rằng lớp LLM là cổng trung lập trong `src/core/llm.py` cộng adapter theo nhà cung cấp (hiện là Anthropic, `src/clients/anthropic_model.py`), thay cho câu interface chuẩn OpenAI-compatible.

**D-015 — Vòng lượt mô hình ở src/turns; dòng log tám khóa là hợp đồng eval**

**Date:** 2026-10-26

**Status:** Accepted

**Bối cảnh:** Cổng mô hình ở `src/core/llm.py` không được import `tools`, trong khi lượt phải gọi `execute_tool`. Bộ eval cần một dòng log cho mỗi lần gọi mô hình, tách khỏi bảy khóa D-014.

**Quyết định:** Vòng lặp của một lượt nằm ở `src/turns`. Dòng log tám khóa của lần gọi mô hình là hợp đồng cho eval. Đổi khóa thì tăng phiên bản hoặc ghi quyết định mới.

**Phương án đã bỏ:** đặt vòng lặp trong `src/core/llm.py`. Luật import không cho core import tools.
