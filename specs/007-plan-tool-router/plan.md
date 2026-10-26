# Implementation Plan: Điều phối tool kế hoạch

**Branch**: `007-plan-tool-router` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-plan-tool-router/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lớp `execute_tool` nhận tên, đầu vào object, và kho người gọi đưa. Catalog sáu tool nằm một file, phiên bản số nguyên `1`. Hàm kiểm tự viết đọc JSON Schema trong catalog. Không thêm thư viện. `ToolError` và `PlanDomainError` giữ nguyên câu. `Exception` khác thành câu chung, và `detail` của log chỉ là tên lớp. Mỗi lần trả kết quả ghi một dòng JSON qua hàm được truyền vào. `SupabasePlanStore(source)` đã đáp ứng FR-012, nên không thêm factory. `src/app.py` thêm một dòng `import db.plan_store`. `src/core` và sáu tool không đổi.

Đối chiếu lựa chọn nằm ở [research.md](./research.md).

## Đã thấy

Đủ chi tiết ở [research.md](./research.md) mục 1. Rút gọn:

- Constructor kho gọi `require_supabase` rồi mới giữ địa chỉ và khóa. Client PostgREST chỉ mở trong bốn phương thức.
- Test thiếu cấu hình trên chính constructor đã có. Hợp đồng ghi rồi đọc trên kho local đã dựng bằng constructor đó.
- `schemas.py` là JSON đầu ra. `tool_router.py` đang là docstring. `app.py` chưa import `db.plan_store`.
- `PlanDomainError` từ `store.add` và `store.get` có thể thoát khỏi tool vì các lời gọi đó nằm ngoài khối đổi lỗi miền.

Chưa đo, người dùng chốt: trên Worker `duration_ms` có thể là 0 vì đồng hồ monotonic đứng trong lúc CPU chạy.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Không thêm. Không `jsonschema`. Không dùng Pydantic cho đầu vào. Pydantic hiện chỉ cho JSON đầu ra ở `src/tools/schemas.py`. Test async bằng `asyncio.run`. Không thêm `pytest-asyncio`.

**Storage**: Không đổi lược đồ. Kho thật vẫn là `SupabasePlanStore`. Test router dùng `MemoryPlanStore` hoặc kho giả trong file test. Không sửa `tests/fakes/memory_plan_store.py`.

**Testing**: `uv run pytest`. Assertion test cũ không sửa. Ba file test mới không skip. Khi Supabase local đang chạy, cả bộ có 0 skipped. Cách chạy nằm ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython cho pytest, và mã phải nạp được cùng app trên Worker. Lát này không thêm route và không gọi LLM.

**Project Type**: Phần điều phối tool của web service. Không có endpoint mới.

**Performance Goals**: Một lần gọi, không gồm lời gọi mô hình, nằm trong ngân sách 3 giây của nguyên tắc VII. Ca tên lạ và ca đầu vào sai không gọi kho. Không thử lại.

**Constraints**: Nguyên tắc I đến VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011 và D-012 trong [docs/DECISIONS.md](../../docs/DECISIONS.md). Implement thêm D-014 vào cuối file đó, không sửa các quyết định cũ. Router không import `db`. `src/core` không sửa. Không đổi chữ ký sáu tool. Không đọc `.env` thật hay `.dev.vars`. Không đọc khóa mô hình. Chỉ bắt `Exception`, không bắt `BaseException`. `detail` unexpected chỉ là tên lớp.

**Scale/Scope**: Sáu tool đã có, một catalog, một hàm điều phối, một dòng import, ba file test mới, một đoạn cập nhật kiến trúc.

## Các lựa chọn đã so

Bản đầy đủ ở [research.md](./research.md) mục 3.

**a. Kiểm đầu vào.** Hàm tự viết đọc schema của catalog. Phần được đọc: `type`, `properties`, `required`, `additionalProperties`, và `items` của mảng chuỗi. Không `enum`. `status` sai chữ nhưng đúng kiểu vẫn vào tool.

**b. Kho.** Không factory. Test FR-012 thiếu cấu hình giữ nguyên hàm đã có. Ca thành công không đọc `_url` hay `_key`: bịt `postgrest_client` trong `db.plan_store`, gọi `list_newest_first()`, đối số `url` và `key` là của nguồn. Ca ghi rồi đọc giữ nguyên hợp đồng spec 006.

**c. Log.** Hàm `log` truyền vào, mặc định `print` một dòng. `ensure_ascii=False`. Không thư viện log mới.

**d. Lỗi không lường.** `detail` là `type(error).__name__`. Thông điệp exception không vào log và không vào `output`. Quyết định này được ghi thành D-014 khi implement, không sửa D-010 đến D-013.

**e. Nạp app.** `test_app_loads_plan_store.py` chạy ở tiến trình con sạch, `PYTHONPATH=src`. Không kiểm `sys.modules` của tiến trình pytest. Một lần kiểm tay: bỏ dòng import thì test đỏ.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Câu mới là câu trong spec. Không thêm tên nhân vật. |
| II. Worker không giữ trạng thái | Đạt | Router không giữ phiên hay hội thoại. Log là một dòng cho lần gọi, không phải kho hội thoại. |
| III. Database qua PostgREST | Đạt | Không thêm chỗ gọi PostgREST. Router không import `db`. |
| IV. LLM qua lớp trung gian | Không áp dụng | Không gọi LLM và không đọc khóa mô hình. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi kế hoạch ra kênh khác. |
| VII. Ngân sách độ trễ với jarvis-desktop | Đạt | Không thêm route desktop. Lần gọi không thêm mạng ngoài lời gọi kho mà tool vốn thực hiện, và không thử lại. |
| VIII. Unit test bắt buộc | Đạt | Ba file test mới. Lệnh nằm ở [quickstart.md](./quickstart.md). |

Không có cổng thất bại.

### Sau Phase 1

Đã đối chiếu [research.md](./research.md), [data-model.md](./data-model.md), [contracts/execute-tool.md](./contracts/execute-tool.md), [contracts/tool-definitions.md](./contracts/tool-definitions.md), [contracts/store-source.md](./contracts/store-source.md), và [quickstart.md](./quickstart.md).

- `Plan`, `Subtask`, `PlanStore`, và chữ ký sáu tool giữ nguyên. Chiều D-011 giữ nguyên: `tool_router` import core và `plan_tools`, nhận `store` qua tham số, không import `db`.
- Catalog không import `plan_tools`. Schema đầu vào không vào `schemas.py`.
- `SupabasePlanStore(source)` là lời dựng duy nhất. Ca thành công quan sát `url` và `key` lúc `list_newest_first` gọi `postgrest_client`, không đọc attribute riêng. `app.py` chỉ thêm import để nạp module. Import không dựng instance và không mở mạng. Test nạp app chạy ở tiến trình con.
- Không thêm dependency. Không bắt `BaseException`. `detail` unexpected không chứa thông điệp. D-014 ghi ba điểm đó cùng lối vào `execute_tool` và hợp đồng log; không đảo D-011 hay D-012.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/007-plan-tool-router/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── execute-tool.md
│   ├── tool-definitions.md
│   └── store-source.md
└── tasks.md             # /speckit-tasks, không tạo ở bước này
```

### Source Code (repository root)

```text
src/tools/
├── tool_definitions.py          # tạo: DEFINITIONS_VERSION và TOOL_DEFINITIONS
├── tool_router.py               # sửa: execute_tool và hàm kiểm
├── plan_tools.py                # không sửa
├── schemas.py                   # không sửa
└── base.py                      # không sửa

src/app.py                       # sửa: một dòng import db.plan_store

src/core/                        # không sửa
src/db/                          # không sửa
src/config/settings.py           # không sửa

tests/
├── test_tool_router.py                  # tạo
├── test_app_loads_plan_store.py         # tạo
├── test_supabase_plan_store_source.py   # tạo
└── (các file test hiện có)              # không sửa

docs/ARCHITECTURE.md             # sửa đoạn trạng thái, §2, §6
```

**Structure Decision**: Catalog đứng riêng vì `schemas.py` là hình đầu ra. Hàm kiểm ở router vì nó đọc catalog rồi gọi tool. App là chỗ nạp module kho, không phải chỗ router tạo kho. Vì vậy `tools` không phụ thuộc `db`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.

## Cách làm khi implement

Viết ba file test trước. Chạy:

```text
uv run pytest tests/test_tool_router.py tests/test_app_loads_plan_store.py tests/test_supabase_plan_store_source.py
```

In output lần fail đó trong phiên, rồi mới viết hoặc sửa file trong `src/` và `docs/ARCHITECTURE.md`. Không sửa assertion của test cũ. Không thêm dependency. Test async bằng `asyncio.run`.

Sau khi mã xong, chạy `uv run pytest`. Khi kho local đang chạy, tổng kết phải có 0 skipped.

`allowed-files.txt` không tạo ở bước plan. Tạo ngay sau `/speckit-tasks`, đúng các dòng ở mục dưới, cộng dòng `specs/007-plan-tool-router/**` nếu danh sách đó chưa có.

## File được tạo hoặc sửa

Danh sách này là nội dung `specs/007-plan-tool-router/allowed-files.txt` ở bước tasks. Mỗi dòng một đường dẫn tương đối, dấu `/`, không có `*` ngoài dòng thư mục spec.

```text
src/tools/tool_definitions.py
src/tools/tool_router.py
src/app.py
tests/test_tool_router.py
tests/test_app_loads_plan_store.py
tests/test_supabase_plan_store_source.py
docs/ARCHITECTURE.md
docs/DECISIONS.md
specs/007-plan-tool-router/**
```

Không đưa vào danh sách, và không sửa: `src/core/`, `src/db/`, `src/tools/plan_tools.py`, `src/tools/schemas.py`, `src/tools/base.py`, `src/config/settings.py`, `pyproject.toml`, `docs/PRODUCT.md`, mọi file test đã có.

## Docs cần cập nhật khi implement

Chưa sửa ở bước plan.

`docs/ARCHITECTURE.md`, chỉ các chỗ sau:

- Đoạn trạng thái đầu file: `src/app.py` phục vụ `/health` và nạp `db.plan_store`. F04 đến F08 vẫn ở `src/core/plans.py` và `src/tools/plan_tools.py`. `execute_tool` điều phối sáu tool khi người gọi đưa kho. Route, Telegram, và LLM chưa gọi router. `SupabasePlanStore` vẫn do người gọi dựng, chưa do route gọi.
- §2, dòng `src/tools/`: `tool_definitions.py` là catalog tên, mô tả, schema đầu vào, và phiên bản. `tool_router.py` kiểm đầu vào rồi gọi `plan_tools`. `plan_tools` vẫn là lớp mỏng.
- §6: thêm một câu rằng mỗi lần điều phối ghi một dòng JSON qua hàm được truyền vào, mặc định in một dòng, không thêm thư viện log. Câu loguru chưa chốt giữ nguyên.

`docs/DECISIONS.md`: thêm D-014 vào cuối file. Không sửa D-010, D-011, D-012, D-013, hay mục nào khác.

**D-014 — execute_tool là lối vào tool call; log bảy khóa là hợp đồng eval**

**Date:** 2026-10-26

**Status:** Accepted

**Bối cảnh:** Sáu tool đã có. Vòng sau nối LLM vào `execute_tool`. Bộ eval cần một dòng log ổn định.

**Quyết định:** `execute_tool` là lối vào duy nhất cho tool call từ LLM. Dòng log bảy khóa của FR-009 trong spec 007 là hợp đồng cho eval. Đổi khóa thì tăng `DEFINITIONS_VERSION` hoặc ghi quyết định mới. `detail` của lỗi unexpected chỉ là tên lớp exception.

**Phương án đã bỏ:** ghi thông điệp exception vào `detail` rồi tìm cách che secret. Router không biết giá trị secret.
