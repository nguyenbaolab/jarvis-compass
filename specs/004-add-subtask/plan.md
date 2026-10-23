# Implementation Plan: Thêm một việc con vào kế hoạch đang có

**Branch**: `004-add-subtask` | **Date**: 2026-10-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-add-subtask/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lát cắt này làm logic của tool F08 `add_subtask` trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Mỗi lần gọi thêm đúng một việc con vào cuối một kế hoạch đã có. Luật dựng việc con mới nằm ở đúng một hàm `new_subtask` trong `src/core/plans.py`: chuẩn hóa tiêu đề, từ chối tiêu đề `None` hoặc rỗng bằng câu `Việc con không được để trống.`, cấp `id`, đặt `SubtaskStatus.PENDING`. `normalize_new_plan` và `add_subtask` cùng gọi hàm đó. Tool là lớp mỏng như `update_subtask`: kiểm hết đầu vào trong core, rồi `store.get`, rồi `append_subtask`, rồi `store.replace`. Không thêm phương thức vào `PlanStore` hay `MemoryPlanStore`. Kết quả thành công dùng lại `_plan_json`. `Plan`, `Subtask`, và `SubtaskStatus` không đổi trường hay kiểu. Test cũ của `create_plan` không sửa assertion. Lý do từng lựa chọn nằm ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `src/core/plans.py` chỉ dùng thư viện chuẩn (`dataclasses`, `enum`, `typing`, `unicodedata`, `uuid`). `new_subtask` dùng `_nfc_strip` và `uuid` đã có. JSON dùng lại `_plan_json` và `PlanJson` trong `src/tools/plan_tools.py` cùng `src/tools/schemas.py` (Pydantic 2 đã có qua FastAPI). `ToolResult` và `ToolError` ở `src/tools/base.py`. Không thêm package. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

**Storage**: Dùng lại `PlanStore.get` và `PlanStore.replace`. Không thêm phương thức vào `PlanStore` hay `MemoryPlanStore`. Supabase qua PostgREST thuộc F03 và nằm ngoài lát cắt này. Lát cắt này không nối kho thật.

**Testing**: pytest, lệnh `uv run pytest`. Không cần database, `.env`, hay `pywrangler`. Test mới nằm ở `tests/test_add_subtask.py`. `tests/test_create_plan.py` không sửa assertion và phải tiếp tục pass. Không bỏ test, không tắt test.

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã sẽ nằm trong Cloudflare Python Workers khi được gọi sau này. Lát cắt này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần thêm là một lần `get` rồi một lần `replace` trên store được truyền vào. Hàm không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011 trong [docs/DECISIONS.md](../../docs/DECISIONS.md): luật miền và cổng ở core, tool là lớp mỏng, core không import tools. Không store tầm module. Không driver database. Type hint cho hàm public. Comment tiếng Việt. `new_subtask` là chỗ duy nhất của luật dựng việc con mới. Không đổi trường hay kiểu của `Plan`, `Subtask`, `SubtaskStatus`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`.

**Scale/Scope**: Một hàm tool public `add_subtask`. Core thêm `new_subtask` và `append_subtask`, và `normalize_new_plan` gọi `new_subtask`. Tạo, liệt kê, mở, và cập nhật trạng thái giữ hành vi đã chốt.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Tool trả một kế hoạch hoặc một câu từ chối. Câu từ chối không nêu tên nhân vật AI khác. |
| II. Worker không giữ trạng thái | Đạt | Không thêm store tầm module. Hàm nhận `PlanStore` do người gọi truyền vào, cùng cách với F04 đến F07. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không mở kết nối database. Ghi bằng `PlanStore.replace` trên store được truyền vào. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Store trong test không phải nguồn sự thật của sản phẩm. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP. Hàm không chờ I/O, nên không chiếm ngân sách 3 giây khi được nối sau. |
| VIII. Unit test bắt buộc | Đạt | Kiểm chứng là pytest trên CPython, mô tả ở [quickstart.md](./quickstart.md). |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/add-subtask.md](./contracts/add-subtask.md), và [research.md](./research.md).

- `Plan`, `Subtask`, và `SubtaskStatus` không thêm trường và không đổi kiểu. Việc con mới dùng `id: str`, `title: str`, `status: SubtaskStatus`.
- `new_subtask` là chỗ duy nhất chuẩn hóa tiêu đề, từ chối `None` hoặc rỗng, cấp `id` bằng `uuid.uuid4()`, và gán `PENDING`. `normalize_new_plan` gọi hàm đó. `append_subtask` chỉ ghép tuple và giữ `id`, `goal`, `created_order`.
- `add_subtask` nhận `store` keyword-only, không có giá trị mặc định. `normalize_plan_id` và `new_subtask` chạy trước `store.get`. Ghi bằng `replace` đã có. `PlanStore` và `MemoryPlanStore` không thêm phương thức. Nguyên tắc II vẫn đạt.
- Lớp tool gọi core, dùng lại `_plan_json` và `PlanJson`, đổi lỗi miền thành `ToolError`. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Chiều phụ thuộc giữ nguyên: tools import core. D-011 không bị đảo.
- Contract cấm gọi PostgREST, LLM, HTTP, và Telegram. `src/db/` không đổi. Nguyên tắc III, IV, VI vẫn đạt. Quy ước Pydantic cho response của tool vẫn đạt vì JSON đi qua `PlanJson` đã có.
- Ba tình huống từ chối là `ToolError`, store không đổi. Thêm được là `ToolResult`. Nguyên tắc VIII vẫn đạt vì các tình huống đó quan sát được bằng pytest, và test cũ của `create_plan` không sửa assertion.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/004-add-subtask/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── add-subtask.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # thêm new_subtask và append_subtask; normalize_new_plan gọi new_subtask

src/tools/
├── base.py                      # đã có: ToolResult, ToolError; không đổi
├── schemas.py                   # PlanJson và SubtaskJson giữ nguyên
└── plan_tools.py                # thêm add_subtask; dùng lại _plan_json

tests/
├── fakes/
│   └── memory_plan_store.py     # không đổi; dùng get và replace đã có
├── test_add_subtask.py          # User Story 1 và 2
├── test_create_plan.py          # không sửa assertion
└── test_health.py               # đã có, phải vẫn pass
```

`src/tools/tool_router.py`, `src/api/`, `src/db/`, `src/clients/`, `src/scheduler/`, `src/app.py`, và các module `src/core/` khác không nằm trong lát cắt này. `src/app.py` đã import `tools.plan_tools`. Thêm hàm trong file đó không tạo store và không gọi mạng.

**Structure Decision**: Luật dựng việc con mới là `new_subtask` trong `src/core/plans.py`. Ghép vào cuối là `append_subtask` trong cùng file. `add_subtask` trong `src/tools/plan_tools.py` là lớp mỏng. Hình JSON dùng lại `_plan_json`. `PlanStore` không thêm phương thức.

### Docs cần cập nhật

[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) câu trạng thái đầu file hiện nói logic F04, F05, F06, và F07. Khi implement làm xong, câu đó phải nói thêm F08, vì lúc đó câu hiện tại sẽ sai. Bước tài liệu này không sửa file đó.

Contract và data-model của F04 đến F07 vẫn đúng: lát này không đổi hình JSON và không đổi trường model. Không sửa các file đó.

[docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên dòng F08 gốc. Không sửa file đó trong lát cắt này.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
