# Data model: Lưu kế hoạch vào kho Supabase

Miền người gọi nhìn thấy giữ nguyên [src/core/plans.py](../../src/core/plans.py). Hai mốc thời gian chỉ có trên dòng việc con. Cách ghi và cách chọn trigger nằm ở [research.md](./research.md). Hành vi cổng nằm ở [contracts/plan-store.md](./contracts/plan-store.md).

## Miền, không đổi

`Plan`: `id: str`, `goal: str`, `subtasks: tuple[Subtask, ...]`, `created_order: int`.

`Subtask`: `id: str`, `title: str`, `status: SubtaskStatus`, `note: str | None`.

`SubtaskStatus`: `pending`, `done`, `skipped`.

`PlanStore`: `add`, `list_newest_first`, `get`, `replace`. Cả bốn là `async`. Không thêm phương thức.

`PlanDomainError` đã có. Store dùng nó cho hai câu trong spec. Không thêm lớp miền.

## plans

Một dòng là một kế hoạch đang có. Không có cờ xóa.

| Cột | Kiểu | Luật |
|-----|------|------|
| `id` | `uuid` primary key, default `gen_random_uuid()` | Người gọi không chọn. Chuỗi đọc ra là danh tính trong `Plan.id`. |
| `goal` | `text not null` | Giữ nguyên chuỗi đã chuẩn hóa trước khi vào store. Store không NFC lại. |
| `created_order` | `bigint generated always as identity` unique | Liệt kê: số lớn hơn đứng trước. `replace` không sửa cột này. |

Không cột mốc thời gian trên `plans`. Spec chỉ đòi hai mốc cho việc con.

## subtasks

| Cột | Kiểu | Luật |
|-----|------|------|
| `id` | `uuid` primary key | Id miền đã cấp lúc tạo việc. Store không cấp lại khi `replace`. |
| `plan_id` | `uuid not null` references `plans(id)` on delete cascade | Mọi việc thuộc một kế hoạch. |
| `title` | `text not null` | Giữ nguyên chuỗi đã lưu. |
| `status` | `text not null` | `CHECK (status in ('pending', 'done', 'skipped'))`. Mapper vẫn chỉ chấp nhận ba mã khi đọc. |
| `note` | `text` null | `CHECK (note IS NULL OR note <> '')`. Không có ghi chú là `NULL`, không phải `""`. |
| `position` | `integer not null` | Gốc 0 theo thứ tự mảng lúc ghi. Unique `(plan_id, position)` deferrable initially deferred. |
| `created_at` | `timestamptz not null default now()` | Lần insert. Mọi update sau giữ giá trị cũ. |
| `status_changed_at` | `timestamptz not null default now()` | Lần insert bằng `created_at` trong cùng transaction. Update chỉ đổi khi `status` đổi. |

Đọc sắp việc con theo `position` tăng dần. Không sắp theo `title`, `created_at`, hay `status_changed_at`.

## Ánh xạ dòng sang miền

`PlanRow` và `SubtaskRow` là Pydantic ở `src/db/models.py`.

`SubtaskRow.status` là `str`. Không dùng `SubtaskStatus` và không dùng `Literal` ba mã trên model dòng. Hàm ánh xạ trong `src/db/plan_store.py` dựng `Subtask` sau khi kiểm ba mã. Mã khác thì lỗi cả kế hoạch, trước khi có `Plan` trả về. Test FR-011 gọi hàm đó với dòng giả, không cần kho. `CHECK` trên cột chặn mọi nơi ghi; dòng giả là dữ liệu đọc từ kho chứa trạng thái lạ.

`SubtaskRow.note` là `str | None`. `NULL` thành `None`. `""` cũng thành `None` lúc đọc, phòng dòng cũ; đường ghi không gửi `""`, và `CHECK` từ chối `""`.

`created_at` và `status_changed_at` có trên `SubtaskRow` để test đọc mốc. Chúng không có tham số nào trong lời gọi `Subtask(...)`.

`created_order` trên dòng là số JSON, thành `int` của `Plan`.

Việc con nhúng trong kế hoạch thiếu khóa `subtasks` là lỗi ánh xạ, không phải kế hoạch không có việc. Mảng rỗng là kế hoạch không có việc.

## Hàm SQL trong cùng migration

`add_plan(goal text, subtasks jsonb) returns jsonb`

`replace_plan(plan_id uuid, goal text, subtasks jsonb) returns void`

Cả hai chạy một transaction, mô tả ở [research.md](./research.md) mục 3. `add_plan` trả kế hoạch vừa ghi, đủ để dựng `Plan`, gồm việc con theo `position`. `replace_plan` trả void. Lần đọc sau là `select`. Hình bọc JSON của `add_plan` khóa bằng test.

Trigger `BEFORE UPDATE` trên `subtasks` giữ `created_at` và áp FR-013 cho `status_changed_at`. Hàm trigger nằm ở schema `internal` để PostgREST không phơi nó thành RPC.

## Quyền

RLS bật trên cả hai bảng. Không policy cho `anon` hay `authenticated`.

`service_role`: `select`, `insert`, `update`, `delete` trên hai bảng; `usage` và `select` trên sequence của `created_order`; `execute` trên `add_plan` và `replace_plan`.

`public`, `anon`, `authenticated`: không còn quyền trên hai bảng, trên sequence của `created_order`, và trên hai hàm đó. Hàm trigger không được `execute` qua PostgREST.

## Bản trong bộ nhớ

`MemoryPlanStore` không có cột và không có mốc. `replace` khi không thấy id ném `PlanDomainError("Không có kế hoạch với danh tính này.")` và không thêm dòng. Các hành vi `add`, `list_newest_first`, và `get` giữ nguyên, gồm so id bằng `==`.
