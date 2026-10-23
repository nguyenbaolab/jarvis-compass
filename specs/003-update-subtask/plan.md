# Implementation Plan: Đánh dấu việc con xong hoặc chưa xong

**Branch**: `003-update-subtask` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-update-subtask/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lát cắt này làm logic của tool F07 `update_subtask` trong [docs/PRODUCT.md](../../docs/PRODUCT.md). `Subtask` trong `src/core/plans.py` thêm `id` và `status`. `status` có kiểu `SubtaskStatus`. `class SubtaskStatus(StrEnum)` có `PENDING = "pending"` và `DONE = "done"`. `title` giữ tên và nghĩa. Việc con mới do `normalize_new_plan` tạo có `id` là `str(uuid.uuid4())` và `status` là `SubtaskStatus.PENDING`. `update_subtask` kiểm hết đầu vào trong core trước khi gọi `store.get`: danh tính kế hoạch, danh tính việc con, rồi trạng thái. Sau đó mới tra kế hoạch và việc con thuộc kế hoạch. Đổi trạng thái trả về `Plan` mới, cùng `id`, `goal`, `created_order`, và cùng thứ tự việc con. `PlanStore.replace` ghi kế hoạch đó. Kết quả thành công dùng lại `PlanJson`. Không thêm package. Lý do từng lựa chọn nằm ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `src/core/plans.py` chỉ dùng thư viện chuẩn (`dataclasses`, `enum`, `typing`, `unicodedata`, `uuid`). `SubtaskStatus` là `StrEnum` của thư viện chuẩn. Không dùng `unicodedata` cho danh tính hay cho trạng thái. JSON dùng lại `PlanJson` và `SubtaskJson` trong `src/tools/schemas.py` (Pydantic 2 đã có qua FastAPI). `SubtaskJson` thêm `id` và `status`. `SubtaskJson.status` khai báo đúng hai giá trị `"pending"` và `"done"`. `ToolResult` và `ToolError` ở `src/tools/base.py`. Không thêm package. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

**Storage**: `PlanStore` thêm `replace(plan: Plan) -> None`. `MemoryPlanStore` trong `tests/fakes/` cài phương thức đó: đổi kế hoạch có cùng `id`, không thêm kế hoạch mới. Supabase qua PostgREST thuộc F03 và nằm ngoài lát cắt này. Lát cắt này không nối kho thật.

**Testing**: pytest, lệnh `uv run pytest`. Không cần database, `.env`, hay `pywrangler`. Test mới nằm ở `tests/test_update_subtask.py`. Assertion hình việc con trong `tests/test_create_plan.py`, `tests/test_get_plans.py`, và `tests/test_get_plan_detail.py` được cập nhật vì [spec.md](./spec.md) FR-003 thêm `id` và `status` vào kết quả tạo, liệt kê, và mở. Các assertion mục tiêu, thứ tự, NFC, từ khóa, và câu từ chối cũ giữ nguyên. Không bỏ test, không tắt test.

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã sẽ nằm trong Cloudflare Python Workers khi được gọi sau này. Lát cắt này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần cập nhật là một lần `get` rồi, khi trạng thái đổi, một lần `replace` trên store được truyền vào. Hàm không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011 trong [docs/DECISIONS.md](../../docs/DECISIONS.md): luật miền và cổng ở core, tool là lớp mỏng, core không import tools. Không store tầm module. Không driver database. Type hint cho hàm public. Comment tiếng Việt. Ba bước kiểm đầu vào chỉ nằm ở `src/core/plans.py` và chỉ dùng thư viện chuẩn. Hình JSON một kế hoạch chỉ nằm ở `PlanJson`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`. `Plan` không thêm trường. `Subtask.title` giữ kiểu `str`.

**Scale/Scope**: Một hàm tool public `update_subtask`. Core thêm chuẩn hóa danh tính việc con, chuẩn hóa trạng thái, và hàm trả về `Plan` sau khi đổi trạng thái một việc con. Tạo, liệt kê, và mở giữ hành vi đã chốt, trừ hình việc con thêm `id` và `status` theo [spec.md](./spec.md) FR-003.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Tool trả một kế hoạch hoặc một câu từ chối. Câu từ chối không nêu tên nhân vật AI khác. |
| II. Worker không giữ trạng thái | Đạt | Không thêm store tầm module. Hàm nhận `PlanStore` do người gọi truyền vào, cùng cách với F04, F05, và F06. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không mở kết nối database. Ghi trạng thái bằng `PlanStore.replace` trên store được truyền vào. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Store trong test không phải nguồn sự thật của sản phẩm. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP. Hàm không chờ I/O, nên không chiếm ngân sách 3 giây khi được nối sau. |
| VIII. Unit test bắt buộc | Đạt | Kiểm chứng là pytest trên CPython, mô tả ở [quickstart.md](./quickstart.md). |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/update-subtask.md](./contracts/update-subtask.md), và [research.md](./research.md).

- `Subtask` thêm `id: str` và `status: SubtaskStatus`. `title` giữ kiểu `str`. `Plan` không thêm trường. `class SubtaskStatus(StrEnum)` có `PENDING = "pending"` và `DONE = "done"`. JSON vẫn xuất chuỗi `"pending"` hoặc `"done"`. `SubtaskJson.status` khai báo đúng hai giá trị đó.
- `normalize_new_plan` gán `id` bằng `uuid.uuid4()` và `status` bằng `SubtaskStatus.PENDING`. `PlanStore.add` không viết lại việc con. `normalize_subtask_status` trả về `SubtaskStatus`. `replace_subtask_status` nhận `SubtaskStatus` và trả về `Plan` mới chỉ khi trạng thái đổi. `PlanStore.replace` ghi kế hoạch có cùng `id`.
- `update_subtask` nhận `store` keyword-only, không có giá trị mặc định. Ba hàm chuẩn hóa chạy trước `store.get`. `MemoryPlanStore` cài `replace`. Nguyên tắc II vẫn đạt.
- Lớp tool gọi core, dùng lại `_plan_json` và `PlanJson`, đổi lỗi miền thành `ToolError`. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Chiều phụ thuộc giữ nguyên: tools import core. D-011 không bị đảo.
- Contract cấm gọi PostgREST, LLM, HTTP, và Telegram. `src/db/` không đổi. Nguyên tắc III, IV, VI vẫn đạt. Quy ước Pydantic cho response của tool vẫn đạt vì `SubtaskJson` và `PlanJson` nằm ở `src/tools/schemas.py`.
- Năm tình huống từ chối là `ToolError`, store không đổi. Cập nhật được, kể cả đặt lại đúng trạng thái đang có, là `ToolResult`. Nguyên tắc VIII vẫn đạt vì các tình huống đó quan sát được bằng pytest.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/003-update-subtask/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── update-subtask.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # Subtask thêm id và status; thêm chuẩn hóa và replace_subtask_status; PlanStore thêm replace

src/tools/
├── base.py                      # đã có: ToolResult, ToolError; không đổi
├── schemas.py                   # SubtaskJson thêm id và status; PlanJson giữ ba khóa
└── plan_tools.py                # thêm update_subtask; _plan_json xuất id và status

tests/
├── fakes/
│   └── memory_plan_store.py     # thêm replace; add giữ nguyên việc con được giao
├── test_update_subtask.py       # User Story 1 và 2
├── test_create_plan.py          # cập nhật assertion hình việc con
├── test_get_plans.py            # cập nhật assertion hình việc con
├── test_get_plan_detail.py      # cập nhật assertion hình việc con
└── test_health.py               # đã có, phải vẫn pass
```

`src/tools/tool_router.py`, `src/api/`, `src/db/`, `src/clients/`, `src/scheduler/`, `src/app.py`, và các module `src/core/` khác không nằm trong lát cắt này. `src/app.py` đã import `tools.plan_tools`. Thêm hàm trong file đó không tạo store và không gọi mạng.

**Structure Decision**: Danh tính việc con và trạng thái là trường của `Subtask` trong `src/core/plans.py`. Ba bước kiểm đầu vào là hàm thuần trong file đó. `update_subtask` trong `src/tools/plan_tools.py` là lớp mỏng. Hình JSON dùng lại `PlanJson`. `Plan` không thêm trường.

### Docs cần cập nhật

[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) câu trạng thái đầu file hiện nói logic F04, F05, và F06. Khi implement làm xong, câu đó phải nói thêm F07, vì lúc đó câu hiện tại sẽ sai. Bước tài liệu này không sửa file đó.

Các contract và data-model của F04, F05, và F06 vẫn mô tả việc con chỉ có `title`. Đó là hình của lát cắt cũ. Hình mới nằm ở [contracts/update-subtask.md](./contracts/update-subtask.md). Khi implement làm xong, mỗi file sau đây thêm một dòng trỏ tới contract đó, không chép lại luật: [create-plan.md](../001-create-list-plans/contracts/create-plan.md), [get-plans.md](../001-create-list-plans/contracts/get-plans.md), [get-plan-detail.md](../002-get-plan-detail/contracts/get-plan-detail.md), và [data-model của F04/F05](../001-create-list-plans/data-model.md). Bước này không sửa các file đó.

[docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên dòng F07 gốc. Không sửa file đó trong lát cắt này.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
