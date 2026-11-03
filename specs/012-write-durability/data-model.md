# Data model: Độ bền ghi

Không có thực thể kế hoạch mới. Thêm một số trên kế hoạch đã có. Việc con không có trường mới.

## Plan

Ở `src/core/plans.py`. Thêm trường `version: int`, không giá trị mặc định. Thiếu đối số khi gọi `Plan(...)` là lỗi ngay.

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `version` | `int` | Số đã đọc từ kho. `add` tạo kế hoạch với `0`. `replace` thành công làm bản trong kho thành số đã đọc cộng 1. Bản `Plan` người gọi đang cầm không tự tăng. |

`_plan_with_subtasks` chép `version` từ plan đã đọc. Không đặt 0.

`plan_from_row` đọc `version` từ dòng. `PlanRow.version` là `int` bắt buộc, không mặc định. Thiếu khóa là lỗi ánh xạ.

`_PLAN_COLUMNS` trong `src/db/client.py` phải có `version` để `get` và `list_newest_first` đọc được. Thiếu cột này thì mọi lần đọc lỗi, vì `PlanRow.version` bắt buộc.

JSON tool (`PlanJson`, `SubtaskJson`) không thêm trường. Mô hình không nhận `version`.

## Bảng plans

Cột mới trong migration `supabase/migrations/20261103205500_plans_version.sql`:

| Cột | Kiểu | Quy tắc |
|---|---|---|
| `version` | `integer not null default 0` | Hàng có sẵn thành 0 khi thêm cột. Hàng `add_plan` tạo sau đó cũng 0. |

`subtasks` không thêm cột.

## add_plan

Trong cùng file migration mới, thân `add_plan` được thay bằng `create or replace`. Chữ ký giữ `(text, jsonb)`. Quyền giữ như hàm cũ: `revoke all on function public.add_plan(text, jsonb) from public, anon, authenticated`, rồi `grant execute on function public.add_plan(text, jsonb) to service_role`. JSON trả về có `version`. Hàng mới là 0 nhờ default của cột. `insert` không cần liệt kê cột `version`.

## replace_plan

Chữ ký mới: `replace_plan(plan_id uuid, goal text, subtasks jsonb, expected_version integer) returns void`.

Kiểm version và tăng version phải atomic. Một trong hai cách:

- Một câu `update ... where id = plan_id and version = expected_version`. Không có hàng thì mới phân biệt `plan_missing` và `plan_version_conflict`.
- Hoặc `select ... for update` rồi mới so. So bằng tay thì dùng `is distinct from`.

Không `select` rồi so mà không khóa. Lệch version hoặc không có hàng: không sửa `plans`, không sửa `subtasks`. Khớp: làm đúng phần sửa goal và việc con đang có, và bản lưu có `version` bằng số đã đọc cộng 1.

Drop chữ ký cũ `(uuid, text, jsonb)` trong cùng file. Hàm mới không thừa hưởng quyền của hàm cũ. Sau khi tạo chữ ký mới, đúng như file migration cũ:

`revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated`

rồi

`grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role`.

## PlanConflictError

Lớp trong `src/core/plans.py`. Không kế thừa `PlanDomainError`. Không chứa câu người dùng.

`SupabasePlanStore.replace` ném lớp này khi RPC trả `plan_version_conflict`. `MemoryPlanStore.replace` ném lớp này khi `plan.version` khác `version` đang lưu, và không gán đè phần tử trong danh sách. Khi khớp, bản lưu trong bộ nhớ là plan đã ghi với `version + 1`.

## Hiệu lực lần ghi

Không phải thực thể kho. Nằm ở `src/tools`, gắn trên `ToolResult` bằng trường tùy chọn mặc định trống. Ba dạng:

| Dạng | Khi nào | Chuỗi người dùng thấy nếu lượt không kết thúc bình thường |
|---|---|---|
| Đã lưu | Tool ghi trả thành công | Một dòng theo mẫu spec, có số thứ tự |
| Chưa chắc | Lời gọi ghi quá hạn | `Chưa chắc thay đổi đã được lưu.` |
| Từ chối | `PlanConflictError` | `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` |

Lần đọc quá hạn không có hiệu lực lần ghi. Câu của lần đó vẫn là `Không thực hiện được yêu cầu này.`

Trường này không đưa vào tin nhắn gửi mô hình. `output` vẫn là chữ tool trả.
