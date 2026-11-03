# Implementation Plan: Độ bền ghi

**Branch**: `012-write-durability` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-write-durability/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Tool chờ mỗi lời gọi kho bằng `asyncio.wait_for` trên số giây còn lại, nên lượt không bị một lời gọi kho chiếm quá ngân sách. Trần HTTP 20 giây chỉ giải phóng kết nối. Hai lần ghi cùng một kế hoạch, kể cả khi cùng đọc bản cũ rồi mới ghi, không xóa thay đổi của nhau trong im lặng: `replace` so `version` một cách atomic, lệch thì từ chối và không đổi kho. Lượt đã ghi mà không kết thúc bình thường trả bản ghép những gì đã lưu, thay cho hai câu lỗi chung. Chi tiết ở [research.md](./research.md).

Schema trong file migration mới đã được duyệt, gồm cột `version`, `replace_plan` có `expected_version`, và bỏ chữ ký cũ. Bước sửa này không tạo `tasks`. Thêm trường `version` trên `Plan` trong `src/core` đã được duyệt trước plan.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `postgrest` và `httpx` đã có. `AsyncPostgrestClient` nhận `http_client`. Không thêm gói. Không driver TCP. `src/core/plans.py` vẫn chỉ thư viện chuẩn.

**Storage**: Supabase qua PostgREST. File mới `supabase/migrations/20261103205500_plans_version.sql`. Không sửa `supabase/migrations/20261025021100_plans_and_subtasks.sql`. Cột `plans.version integer not null default 0`, hàng có sẵn thành 0. `add_plan` được `create or replace`, giữ chữ ký `(text, jsonb)` và quyền, JSON trả về có `version`. `replace_plan` bỏ chữ ký `(uuid, text, jsonb)`, tạo `(uuid, text, jsonb, integer)`. Kiểm version và tăng version là atomic: một `update ... where id = ... and version = expected_version`, không có hàng thì phân biệt `plan_missing` và `plan_version_conflict`; hoặc `select ... for update` rồi so bằng `is distinct from`. Không `select` rồi so mà không khóa. Hàm mới không thừa hưởng quyền hàm cũ: `revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated`, rồi `grant execute ... to service_role`.

**Testing**: `uv run pytest`. Ca timeout và ca version trên kho giả trong `tests/fakes`, không mở mạng. Ca RPC trên Supabase local sau `db reset`, mô tả ở [quickstart.md](./quickstart.md), plan không chạy. Timeout trên Worker là chưa kiểm chứng.

**Target Platform**: CPython cho pytest. Cùng mã store chạy trên Cloudflare Python Workers. Hành vi timeout của httpx trên Pyodide chưa được quan sát.

**Project Type**: Phần ghi kho và lượt của một web service. Không thêm route. Không thêm tool.

**Performance Goals**: Một người dùng, [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. `asyncio.wait_for` không để một lời gọi kho chiếm quá phần ngân sách còn lại. Lượt không vượt 20 giây vì lời gọi kho chưa trả về. Trần HTTP 20 giây không phải hạn này.

**Constraints**: Nguyên tắc I đến VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-010: PostgREST, không driver TCP. D-011: core không import tools hay db. D-014 và D-015: không đổi bộ khóa log. Không đổi lời hướng dẫn, `PROMPT_VERSION`, bộ định nghĩa, `DEFINITIONS_VERSION`, bộ câu đánh giá, cách chấm. Không thêm trường ngày. Timeout chỉ trong `src/db` và `src/tools`. Bản ghép và chuỗi cố định không ở `src/core`.

**Scale/Scope**: Một cột, thân `add_plan` thay bằng `create or replace` giữ chữ ký `(text, jsonb)`, một chữ ký `replace_plan` mới sau khi bỏ chữ ký cũ, một lớp lỗi, một module chuỗi, trường tùy chọn trên `ToolResult`. `_PLAN_COLUMNS` trong `src/db/client.py` phải có `version` để `get` và `list_newest_first` đọc được. Thiếu thì mọi lần đọc lỗi, vì `PlanRow.version` bắt buộc. Test cũ chỉ đổi assertion khi khẳng định đúng một trong ba hành vi ở Assumptions của spec. Thêm `version` vào chỗ dựng `Plan` thì được.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|---|---|---|
| I. Một nhân vật duy nhất | Đạt | Câu mới là chữ trơn của JARVIS. Không có tên nhân vật khác. |
| II. Worker không giữ trạng thái | Đạt | `version` nằm trong Postgres. Kho giả chỉ trong test. |
| III. Database qua PostgREST | Đạt | Vẫn `src/db/client.py` và `postgrest`. Timeout đi qua `http_client` của client đó. Không thêm driver TCP. |
| IV. LLM qua lớp trung gian | Đạt | Không đổi cổng mô hình, lời hướng dẫn, hay adapter. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Vẫn bảng `plans` và `subtasks`. Không ghi Google Tasks hay Keep. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không thêm đường desktop. Ngân sách 20 giây là ngân sách lượt đã có. |
| VIII. Unit test bắt buộc | Đạt | Ca mới trên kho giả. Assertion cũ chỉ đổi khi đụng ba hành vi spec đã nêu. |
| D-011, trường `Plan` | Đạt, đã duyệt | Thêm `version: int` không mặc định. Duyệt trước plan. Không phải lý do dừng. |
| Schema migration | Đã duyệt | Cột, `expected_version`, bỏ chữ ký cũ, kiểm atomic, và revoke/grant đã duyệt. Plan không áp migration và không tạo tasks. |

Không có cổng constitution nào thất bại. Cổng schema không phải vi phạm constitution. Thiết kế đã được duyệt. Bước này vẫn không tạo tasks.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [research.md](./research.md), và ba contract.

- `Plan.version` không có mặc định. Core không import tools hay db. Chuỗi người dùng không nằm trong core. D-011 giữ hướng phụ thuộc.
- Bốn phương thức `PlanStore` giữ nguyên. `replace` đọc version trên plan. Nguyên tắc II: không thêm trạng thái module trong `src/`.
- RPC và select vẫn qua PostgREST. `httpx.AsyncClient` chỉ để đặt timeout cho client PostgREST đã có. Nguyên tắc III giữ.
- Khóa log không đổi. Lời hướng dẫn và bộ định nghĩa không đổi. Nguyên tắc IV giữ.
- Nguyên tắc VIII: quickstart nêu pytest kho giả và pytest kho local. Plan không chạy chúng. Timeout Worker ghi chưa kiểm chứng, không ghi là đạt.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/012-write-durability/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── replace-version.md
│   ├── call-limit.md
│   └── saved-reply.md
└── tasks.md             # không tạo ở bước plan
```

### Source Code (repository root)

```text
src/core/plans.py                 # Plan.version, PlanConflictError, _plan_with_subtasks
src/db/client.py                  # trần HTTP 20 giây qua http_client; replace_plan nhận expected_version; _PLAN_COLUMNS có version
src/db/models.py                  # PlanRow.version
src/db/plan_store.py              # plan_from_row, replace ném PlanConflictError
src/tools/saved_reply.py          # file mới, mọi chuỗi cố định và hàm ghép
src/tools/base.py                 # ToolResult thêm trường tùy chọn
src/tools/plan_tools.py           # wait_for từng lời gọi kho, đổi xung đột thành câu từ chối
src/tools/tool_router.py          # nhận hàm số giây còn lại, mặc định None; giữ khóa log; giữ chữ output
src/turns/llm_turn.py             # truyền lambda: _remaining(started); gọi hàm ghép khi không kết thúc bình thường
supabase/migrations/20261103205500_plans_version.sql
tests/fakes/memory_plan_store.py  # cùng điều kiện xung đột
tests/                            # dựng Plan có version; ca mới cho ba hành vi
```

**Structure Decision**: Một service Python như các lát trước. Không thư mục mới ngoài `src/tools/saved_reply.py` và một file migration. `_PLAN_COLUMNS` thiếu `version` thì `get` và `list_newest_first` lỗi, vì `PlanRow.version` bắt buộc.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Không có vi phạm constitution cần biện minh. Schema đã duyệt. Bước này không tạo tasks.

## Design notes

### Version

Chi tiết cột, RPC, và lớp lỗi ở [data-model.md](./data-model.md) và [contracts/replace-version.md](./contracts/replace-version.md).

`MemoryPlanStore` và `SupabasePlanStore` cùng một điều kiện: version đưa vào khác version đang lưu thì `PlanConflictError` và không ghi. Khớp thì bản đọc sau có version tăng 1.

Tool không thử lại. Câu từ chối đi về mô hình như lỗi tool khác.

Chỗ dựng `Plan` thiếu `version` phải lỗi: `_plan_with_subtasks`, `plan_from_row`, `MemoryPlanStore.add`, và mọi `Plan(...)` trong `tests/`. Không thêm mặc định để chỗ quên trường vẫn chạy.

### Giới hạn thời gian

Chi tiết ở [contracts/call-limit.md](./contracts/call-limit.md).

`run_turn` truyền cho `execute_tool` một hàm không đối số trả số giây còn lại, tức `lambda: _remaining(started)`. Không truyền một số tính sẵn, không truyền mốc thời gian tuyệt đối. Số tính trước `complete` đã cũ khi tool chạy. Tool đọc rồi ghi thì lời gọi sau phải thấy số đã giảm. `_now` trong `llm_turn` là đồng hồ duy nhất mà test bịt.

Tool gọi hàm đó ngay trước mỗi lời gọi kho và chờ bằng `asyncio.wait_for` với số đó. Đây là chỗ bảo đảm FR-001. Số còn lại nhỏ hơn hoặc bằng 0 trước khi một lời gọi kho bắt đầu: không gửi lời gọi, tool trả `Không thực hiện được yêu cầu này.`, không đặt cờ hiệu lực ghi. Lượt tự rơi vào lối hết giờ ở vòng kiểm kế tiếp.

`execute_tool` có mặc định `None`, nghĩa là không giới hạn, chỉ để test cũ. `run_turn` luôn truyền hàm. Một ca đi qua `run_turn` với kho giả không trả lời, chứng minh lượt trả trong hạn.

`postgrest_client` tạo `httpx.AsyncClient` với mức trần cố định 20 giây, hằng riêng trong `src/db`, ghi chú là bằng ngân sách của lượt, truyền bằng `http_client`. Cổng `PlanStore` giữ nguyên nên số còn lại không tới được `SupabasePlanStore`. Timeout httpx tính theo từng pha (connect, read, write, pool), không phải tổng. Mức trần chỉ để giải phóng kết nối, không phải chỗ bảo đảm FR-001.

Kho giả không mở mạng đủ để chứng minh tool bỏ lời gọi treo và lượt trả trong hạn. Hành vi trên Worker vẫn là chưa kiểm chứng. Cách chạy ghi ở [quickstart.md](./quickstart.md). Plan không chạy.

### Bản ghép

Chi tiết ở [contracts/saved-reply.md](./contracts/saved-reply.md).

Sáu mẫu dòng và ba câu chỉ ở `src/tools/saved_reply.py`. Lượt gọi hàm ghép. Không ghép trong core.

`output` gửi mô hình giữ nguyên chữ. Khóa log giữ nguyên.

### Test

Assertion cũ giữ nguyên, trừ khi nó khẳng định một trong ba điều sau: lời gọi kho đã bắt đầu không bị bỏ khi quá hạn, hai lần ghi chạy chồng được xóa im lặng, hoặc lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối mà không kết thúc bình thường vẫn là câu lỗi chung hay văn bản rỗng hoặc chỉ khoảng trắng.

Thêm `version` vào dữ liệu dựng sẵn thì được. Sau `replace` thành công, lần đọc thấy version tăng 1. Chỗ kỳ vọng cả object `Plan` phải dựng số mới đó. Đó là dựng dữ liệu, không phải đổi luật khác.

Ca đi qua `run_turn` với kho giả không trả lời nằm trong danh sách ca mới: lượt phải trả trong hạn.

### Dừng

Thiết kế schema đã được duyệt. Bước sửa plan này không tạo `tasks.md`, không viết file migration, không `db reset`, không `db push`, không deploy. Thứ tự lên production nằm ở [quickstart.md](./quickstart.md) và là việc của bước hoàn tất lát này.
