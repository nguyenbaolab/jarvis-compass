# Implementation Plan: Xem chi tiết một kế hoạch

**Branch**: `002-get-plan-detail` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-get-plan-detail/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lát cắt này làm logic của tool F06 `get_plan_detail` trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Hàm nhận danh tính một kế hoạch và trả về đúng kế hoạch đó. `normalize_plan_id` trong `src/core/plans.py` kiểm `None`, chuỗi rỗng, và chuỗi chỉ khoảng trắng, chỉ bằng thư viện chuẩn. `get_plan_detail` gọi `PlanStore.get(plan_id: str) -> Plan | None`. `src/tools/plan_tools.py` đổi kế hoạch tìm thấy thành `ToolResult` bằng `PlanJson` đã có, và đổi lỗi miền cùng kết quả `None` thành `ToolError`. `Plan`, `Subtask`, và `PlanJson` giữ nguyên. Không thêm package. `MemoryPlanStore` trong `tests/fakes/` cài `get`. Lý do từng lựa chọn nằm ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `normalize_plan_id` trong `src/core/plans.py` chỉ dùng thư viện chuẩn đã có (`dataclasses`, `typing`). Không dùng `unicodedata` cho danh tính. JSON dùng lại `PlanJson` trong `src/tools/schemas.py` (Pydantic 2 đã có qua FastAPI). `ToolResult` và `ToolError` ở `src/tools/base.py`. Không thêm package. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

**Storage**: Đọc một kế hoạch qua `PlanStore.get`. `MemoryPlanStore` trong `tests/fakes/` cài phương thức đó và trả `None` khi không có. Supabase qua PostgREST thuộc F03 và nằm ngoài lát cắt này; lát cắt này không nối kho thật.

**Testing**: pytest, lệnh `uv run pytest`. Không cần database, `.env`, hay `pywrangler`. Test mới nằm ở `tests/test_get_plan_detail.py`. Test của F04 và F05 phải vẫn pass.

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã sẽ nằm trong Cloudflare Python Workers khi được gọi sau này; lát cắt này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần mở là một lần `get` theo id trên store được truyền vào. Hàm không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). Không store tầm module. Không driver database. Type hint cho hàm public. Comment tiếng Việt. Phần kiểm id (`None`, rỗng, chỉ khoảng trắng, `strip`) chỉ nằm ở `src/core/plans.py` và chỉ dùng thư viện chuẩn. Hình JSON một kế hoạch chỉ nằm ở `PlanJson` trong `src/tools/schemas.py`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`. Không đổi trường hay kiểu của `Plan` và `Subtask`.

**Scale/Scope**: Một hàm tool public `get_plan_detail`, hàm `normalize_plan_id`, và `PlanStore.get`. Tạo và liệt kê giữ nguyên hành vi ở [spec tạo và liệt kê](../001-create-list-plans/spec.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Tool trả dữ liệu một kế hoạch hoặc lời từ chối. Lời từ chối không nêu tên nhân vật AI khác. |
| II. Worker không giữ trạng thái | Đạt | Không thêm store tầm module. Hàm nhận `PlanStore` do người gọi truyền vào, cùng cách với F04 và F05. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không mở kết nối database. Đọc một kế hoạch bằng `PlanStore.get` trên store được truyền vào. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Store trong test không phải nguồn sự thật của sản phẩm. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP. Hàm không chờ I/O, nên không chiếm ngân sách 3 giây khi được nối sau. |
| VIII. Unit test bắt buộc | Đạt | Kiểm chứng là pytest trên CPython, mô tả ở [quickstart.md](./quickstart.md). |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/get-plan-detail.md](./contracts/get-plan-detail.md), và [research.md](./research.md).

- `Plan` và `Subtask` giữ nguyên trường và kiểu đã chốt ở [data-model của F04/F05](../001-create-list-plans/data-model.md). `PlanStore` thêm `get(plan_id: str) -> Plan | None`. `normalize_plan_id` báo lỗi miền khi danh tính chưa được đưa, và trả về chuỗi đã `strip` khi còn nội dung.
- `get` so chuỗi đã `strip` bằng `==` với `Plan.id`. Không NFC, không `casefold`. `None` từ `get` thành lời từ chối không có kế hoạch.
- `get_plan_detail` nhận `store` keyword-only, không có giá trị mặc định, và gọi `store.get`. `MemoryPlanStore` cài `get`. Nguyên tắc II vẫn đạt.
- Lớp tool gọi core, dùng lại `_plan_json` và `PlanJson`, đổi lỗi miền thành `ToolError`. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Chiều phụ thuộc giữ nguyên: tools import core.
- Contract cấm gọi PostgREST, LLM, HTTP, và Telegram. `src/db/` không đổi. Nguyên tắc III, IV, VI vẫn đạt. Quy ước Pydantic cho response của tool vẫn đạt vì dùng lại `PlanJson`.
- Id không mở được thì `ToolError`, store không đổi. Id mở được thì `ToolResult` với JSON một kế hoạch. Nguyên tắc VIII vẫn đạt vì cả hai tình huống, gồm phân biệt hoa thường và khoảng trắng hai đầu, quan sát được bằng pytest.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/002-get-plan-detail/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── get-plan-detail.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # thêm normalize_plan_id và PlanStore.get; Plan và Subtask giữ nguyên

src/tools/
├── base.py                      # đã có: ToolResult, ToolError; không đổi
├── schemas.py                   # đã có: PlanJson; không đổi
└── plan_tools.py                # thêm get_plan_detail; create_plan và get_plans giữ nguyên

tests/
├── fakes/
│   └── memory_plan_store.py     # thêm get; add và liệt kê giữ nguyên
├── test_get_plan_detail.py      # User Story 1 và 2
├── test_create_plan.py          # đã có, phải vẫn pass
├── test_get_plans.py            # đã có, phải vẫn pass
└── test_health.py               # đã có, phải vẫn pass
```

`src/tools/tool_router.py`, `src/api/`, `src/db/`, `src/clients/`, `src/scheduler/`, `src/app.py`, và các module `src/core/` khác không nằm trong lát cắt này. `src/app.py` đã import `tools.plan_tools`; thêm hàm trong file đó không tạo store và không gọi mạng.

**Structure Decision**: Phần kiểm id là `normalize_plan_id` trong `src/core/plans.py`. `get_plan_detail` trong `src/tools/plan_tools.py` là lớp mỏng và gọi `store.get`. Hình JSON dùng lại `PlanJson`. `Plan` và `Subtask` giữ nguyên.

### Docs cần cập nhật

[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) §2 nêu tên `PlanStore` cùng `Plan` và `Subtask`. File đó không liệt kê phương thức của `PlanStore`, nên không thêm file đó vào danh sách cập nhật phương thức. Khi implement làm xong, câu trạng thái đầu file đó phải nói logic F06 đã có, vì lúc đó câu hiện tại chỉ nói F04 và F05 sẽ sai. Bước tài liệu này không sửa file đó.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
