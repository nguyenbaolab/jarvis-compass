# Implementation Plan: Tạo và liệt kê kế hoạch

**Branch**: `001-create-list-plans` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-create-list-plans/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lát cắt này làm logic của hai tool trong [docs/PRODUCT.md](../../docs/PRODUCT.md): F04 `create_plan` và F05 `get_plans`. Luật miền nằm ở `src/core/plans.py`: chuẩn hóa NFC rồi strip, từ chối input rỗng, kiểu `Plan` và `Subtask`, cổng `PlanStore`, và lọc từ khóa trong goal. `src/tools/plan_tools.py` gọi core, đổi kết quả thành `ToolResult`, và đổi lỗi miền thành `ToolError`. JSON của tool do `src/tools/schemas.py` sinh; `subtasks` là mảng object `{"title": ...}`, giữ thứ tự. Kiểm chứng dùng `MemoryPlanStore` tạo mới mỗi test, nên chạy được khi chưa có Supabase. Lý do từng lựa chọn nằm ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `src/core/plans.py` chỉ dùng thư viện chuẩn `dataclasses`, `typing`, `unicodedata`, `uuid`. `src/tools/schemas.py` dùng Pydantic 2 đã có qua FastAPI (`BaseModel`, `model_dump_json`). `ToolResult` và `ToolError` ở `src/tools/base.py`. Không thêm package. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Không import `postgrest`, `anthropic`, hay client Telegram trong các module mới.

**Storage**: Cổng `PlanStore` trong `src/core/plans.py`. Bản bộ nhớ `MemoryPlanStore` chỉ ở `tests/fakes/`. Supabase qua PostgREST thuộc F03 và nằm ngoài lát cắt này; `src/db/client.py` và `src/db/models.py` giữ nguyên stub.

**Testing**: pytest, lệnh `uv run pytest`. Không cần database, `.env`, hay `pywrangler`.

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã sẽ nằm trong Cloudflare Python Workers khi được gọi sau này; lát cắt này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần liệt kê trả về toàn bộ tập đang khớp, không phân trang. Hai hàm không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). Không store tầm module. Không driver database. Type hint cho hàm public. Comment tiếng Việt. Luật chuẩn hóa và lọc chỉ nằm ở `src/core/plans.py`. Schema JSON chỉ nằm ở `src/tools/schemas.py`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`.

**Scale/Scope**: Hai hàm tool public, kiểu `Plan`, kiểu `Subtask`, một cổng, một store dành cho test. Mọi kế hoạch tạo thành công đều đang hoạt động.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Tool trả dữ liệu kế hoạch. Thông báo lỗi không nêu tên nhân vật AI khác. |
| II. Worker không giữ trạng thái | Đạt | Store không sống ở tầm module. `PlanStore` là Protocol trong `src/core/plans.py`, không có bản cài đặt trong `src/`. Bản bộ nhớ do test tạo và truyền vào từng lần gọi. |
| III. Database qua PostgREST | Đạt | `src/core/plans.py` không import `src/db` và không mở kết nối database. Bản PostgREST sau này, nếu có, phải đi qua `src/db/client.py`. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Store trong test không phải nguồn sự thật của sản phẩm. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP. Hai hàm không chờ I/O, nên không chiếm ngân sách 3 giây khi được nối sau. |
| VIII. Unit test bắt buộc | Đạt | Kiểm chứng là pytest trên CPython, mô tả ở [quickstart.md](./quickstart.md). |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/create-plan.md](./contracts/create-plan.md), và [contracts/get-plans.md](./contracts/get-plans.md).

- `Plan` và `Subtask` là dataclass trong `src/core/plans.py`. `Plan` không có trường session. `Plan.subtasks` là `tuple[Subtask, ...]`, mỗi `Subtask` một trường `title`. JSON của tool là mảng object `{"title": ...}`, giữ thứ tự. Đầu vào `create_plan` vẫn là danh sách chuỗi.
- `goal`, từng việc con, và từ khóa lọc đi qua NFC rồi `strip`. Giá trị lưu là dạng NFC. So khớp lọc là NFC rồi `casefold` ở cả hai phía. `"tieng"` không khớp `"tiếng"`.
- Hai hàm nhận `store` keyword-only, không có giá trị mặc định. `MemoryPlanStore` nằm dưới `tests/fakes/`. Nguyên tắc II vẫn đạt.
- `src/tools/plan_tools.py` gọi core và đổi kết quả thành `ToolResult`, đổi lỗi miền thành `ToolError`. `src/tools/schemas.py` giữ hình JSON bằng Pydantic. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Chiều phụ thuộc: tools import core; core không import tools.
- Contract cấm gọi PostgREST, LLM, HTTP, và Telegram. `src/db/` không đổi. Nguyên tắc III, IV, VI vẫn đạt. Quy ước Pydantic cho response của tool vẫn đạt, vì schema JSON ở `src/tools/schemas.py`.
- `get_plans` trả danh sách rỗng bằng `ToolResult` thành công. `create_plan` từ chối bằng `ToolError` và không gọi `add`. Nguyên tắc VIII vẫn đạt vì các tình huống đó, gồm hai tình huống NFC trong contract, quan sát được bằng pytest.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/001-create-list-plans/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── create-plan.md
│   └── get-plans.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # src/core/plans.py: Plan, Subtask, normalize_new_plan, lỗi miền, Protocol PlanStore, hàm lọc theo từ khóa trong goal

src/tools/
├── base.py                      # đã có: ToolResult, ToolError
├── schemas.py                   # Pydantic: hình JSON của tool; subtask là object có title
└── plan_tools.py                # lớp mỏng: gọi core, đổi kết quả thành ToolResult, đổi lỗi miền thành ToolError

tests/
├── fakes/
│   ├── __init__.py
│   └── MemoryPlanStore          # PlanStore trong bộ nhớ, chỉ cho test
├── test_create_plan.py          # User Story 1
├── test_get_plans.py            # User Story 2 và 3
└── test_health.py               # đã có, phải vẫn pass
```

`src/tools/tool_router.py`, `src/api/`, `src/db/`, `src/clients/`, `src/scheduler/`, và các module `src/core/` đã có (`llm.py`, `planning.py`, `session.py`) không nằm trong lát cắt này. Lát cắt thêm `src/core/plans.py`.

**Structure Decision**: Logic miền nằm ở `src/core/plans.py`: `Plan`, `Subtask`, `normalize_new_plan`, lỗi miền, `Protocol PlanStore`, và hàm lọc theo từ khóa trong goal. File đó chỉ dùng `dataclasses`, `typing`, `unicodedata`, `uuid`, và không import FastAPI, Pydantic, `src/tools`, hay `src/db`. `src/tools/plan_tools.py` là lớp mỏng: gọi core, đổi kết quả thành `ToolResult`, đổi lỗi miền thành `ToolError`. `src/tools/schemas.py` giữ hình dạng JSON của tool. Model và cổng không đặt thành module riêng trong `src/tools/`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`. `src/app.py` đã import `tools.plan_tools`, nên schema và lớp mỏng đi theo import đó vào bundle của Worker; import không được tạo store. `Plan` đặt ở core vì scheduler (F10) và các tool F06 đến F09 sẽ dùng lại, xem [research.md](./research.md). [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) §2 hiện mô tả `src/core/` là clarify/orchestration (F01, F02) và LLM (F12), và giao planning tools (F04–F09) cho `src/tools/`. Bước tài liệu này không sửa file đó.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
