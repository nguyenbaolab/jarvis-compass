# Data model: Ngày, ưu tiên và sức

Nguồn hành vi là [spec.md](./spec.md). Lý do từng lựa chọn ở [research.md](./research.md). Bước plan không tạo file migration.

## Model miền (`src/core/plans.py`)

Chỉ thư viện chuẩn. Trường mới có mặc định `None` và đứng sau các trường cũ.

### `Priority`

`StrEnum`: `high`, `medium`, `low`. Chữ chủ bot nghe, theo thứ tự, là cao, vừa, thấp.

### `Effort`

`StrEnum`: `S`, `M`, `L`. Hằng `EFFORT_HOURS`: S = 1, M = 3, L = 6. Không cộng giờ ở vòng này.

### `Subtask`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `id` | `str` | Giữ |
| `title` | `str` | Giữ nguyên từng chữ, kể cả tiêu đề cũ đang chứa đoạn ngày |
| `status` | `SubtaskStatus` | `pending`, `done`, `skipped` |
| `note` | `str \| None` | Giữ |
| `scheduled_on` | `date \| None` | Mặc định `None`. Ngày lịch, không giờ |
| `effort` | `Effort \| None` | Mặc định `None` |

### `Plan`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `id` | `str` | Giữ |
| `goal` | `str` | Tên duy nhất. Không cột tên khác |
| `subtasks` | `tuple[Subtask, ...]` | Giữ thứ tự đã lưu |
| `created_order` | `int` | Giữ |
| `version` | `int` | Khóa lạc quan D-021 |
| `priority` | `Priority \| None` | Mặc định `None`. Không có độ gấp |

Không có cột hạn. Hạn là `plan_deadline`: ngày muộn nhất trong các việc `pending` có `scheduled_on`. Việc `done` và `skipped` không tính. Không việc chưa làm nào có ngày thì hạn là `None`.

### Hàm thuần

- `plan_deadline(plan) -> date | None`
- `deadline_clash(after, others) -> Plan | None`. Cùng id với `after` thì bỏ qua. Chỉ dùng khi hạn của `after` khác hạn của bản trước lần dời.
- `date_moves(before, after) -> tuple[Subtask, ...]`. Chỉ việc đổi từ một ngày sang một ngày khác.

`scheduled_on` nhận chuỗi thì phải là ngày ISO `YYYY-MM-DD`. Sai thì `PlanDomainError`. Mã ưu tiên hoặc sức lạ cũng `PlanDomainError`.

## Bảng `plans`

Cột đang có giữ nguyên: `id`, `goal`, `created_order`, `version`, `created_at`.

| Cột mới | Kiểu | Ràng buộc |
|---|---|---|
| `priority` | `text` null | `high`, `medium`, `low`, hoặc null |

## Bảng `subtasks`

Cột đang có giữ nguyên: `id`, `plan_id`, `title`, `status`, `note`, `position`, `created_at`, `status_changed_at`. Trigger `subtasks_keep_clocks` giữ nghĩa: `created_at` không viết lại, `status_changed_at` chỉ đổi khi `status` đổi.

| Cột mới | Kiểu | Ràng buộc |
|---|---|---|
| `scheduled_on` | `date` null | Không giờ, không múi giờ |
| `effort` | `text` null | `S`, `M`, `L`, hoặc null |

## Bảng `subtask_date_moves`

Chỉ thêm dòng. Không đường đọc cho mô hình.

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | `uuid` | Khóa chính, tự sinh |
| `plan_id` | `uuid` | Không khóa ngoại. Not null |
| `subtask_id` | `uuid` | Không khóa ngoại. Not null |
| `from_date` | `date` | Not null |
| `to_date` | `date` | Not null, khác `from_date` |
| `reason` | `text` | Null được |
| `moved_at` | `timestamptz` | Not null. Do lời gọi truyền, không phải `now()` |

Trigger `BEFORE UPDATE OR DELETE` làm lệnh sửa hoặc xóa lỗi. Không có `ON DELETE CASCADE` và không có `ON DELETE RESTRICT` sang `subtasks`. `replace_plan` vẫn được xóa việc con không còn trong payload. Dòng lịch sử của việc đó còn.

Một dòng sinh ra chỉ khi `replace_plan` thấy ngày đang lưu và ngày payload đều khác null và khác nhau. Trống sang ngày, ngày sang trống, và cùng một ngày không sinh dòng.

## RPC

Migration `drop function` đúng chữ ký đang có rồi tạo lại. `create or replace` không đổi chữ ký, và để hàm cũ còn thì lời gọi của Worker cũ không đi vào thân mới. Cấp lại `execute` cho `service_role`. `revoke` khỏi `public`, `anon`, `authenticated`.

### `add_plan(goal text, subtasks jsonb, priority text DEFAULT NULL)`

Chữ ký cũ `add_plan(text, jsonb)` bị bỏ. Lời gọi hai tham số vẫn khớp vì `priority` mặc định null. Hàm vẫn trả object kế hoạch, không void.

| Tham số | Khi Worker cũ không gửi | Khi có |
|---|---|---|
| `priority` | ghi null | `high`, `medium`, `low`, hoặc null |

Mỗi phần tử `subtasks` trên lần tạo. Dòng việc chưa có giá trị để giữ, nên khóa vắng ghi null:

| Khóa | Khi vắng | Khi có |
|---|---|---|
| `scheduled_on` | ghi null | ngày ISO hoặc JSON null |
| `effort` | ghi null | `S`, `M`, `L`, hoặc JSON null |

Không ghi bảng lịch sử.

### `replace_plan`

Chữ ký cũ bốn tham số bị bỏ. Chữ ký mới, vẫn `returns boolean`:

| Tham số | Kiểu | Mặc định |
|---|---|---|
| `plan_id` | `uuid` | không |
| `goal` | `text` | không |
| `subtasks` | `jsonb` | không |
| `expected_version` | `integer` | không |
| `plan_fields` | `jsonb` | `NULL` |
| `move_reason` | `text` | `NULL` |
| `moved_at` | `timestamptz` | `NULL` |

Lời gọi bốn tham số vẫn chạy. `plan_fields` null, hoặc object không có khóa `priority`, thì giữ `plans.priority`. Khóa `priority` có mặt thì đặt. JSON null là xóa.

Trong từng việc con, cùng luật:

| Khóa trong JSON | Khi vắng | Khi có |
|---|---|---|
| `scheduled_on` | giữ ngày đang lưu | đặt ngày, hoặc JSON null thì xóa |
| `effort` | giữ sức đang lưu | đặt `S`, `M`, `L`, hoặc JSON null thì xóa |
| `note` | giữ luật hiện tại: vắng thành null | đặt chữ, hoặc JSON null thì xóa |

Khi có việc đổi từ ngày sang ngày khác, INSERT một dòng `subtask_date_moves` trong cùng hàm, dùng `move_reason` và `moved_at`. `moved_at` null mà vẫn có việc đổi ngày thì hàm lỗi, không gọi `now()`, không ghi kế hoạch. Worker bản cũ không gửi ngày nên không rơi vào nhánh này. Worker bản mới truyền `moved_at` khi gọi tool dời ngày, lấy từ `TurnContext.instant`.

`plan_missing` và `plan_version_conflict` giữ nguyên. Khóa version chỉ so kế hoạch đang ghi.

## Đọc

`list_plans` và `get_plan` select thêm `plans.priority`, `subtasks.scheduled_on`, `subtasks.effort`.

`PlanRow.priority: str | None = None`. `SubtaskRow.scheduled_on: str | None = None`. `SubtaskRow.effort: str | None = None`.

`plan_from_row` đưa ba trường vào `Plan` và `Subtask`. Không đọc `subtask_date_moves` vào model.

## JSON tool

`SubtaskJson`: `id`, `title`, `status`, `note`, `scheduled_on`, `effort`.

`PlanJson`: `id`, `goal`, `priority`, `subtasks`.

Không khóa lịch sử. Không khóa hạn. Không khóa độ gấp.

## Cổng lưu và đồ giả

`PlanStore.add` thêm `priority: Priority | None = None`, keyword. Lời gọi `(goal, subtasks)` vẫn chạy. `SupabasePlanStore.add` đưa giá trị xuống tham số `priority` của `add_plan`. `None` thành SQL null.

`PlanStore.replace` thêm `move_reason: str | None = None` và `moved_at: datetime | None = None`, keyword, có mặc định. Chỉ tool dời ngày truyền hai giá trị này. `SupabasePlanStore.replace` luôn gửi `plan_fields` có khóa `priority`, lấy từ `plan.priority`. `None` thành JSON null, tức là xóa. Payload từng việc luôn có khóa `scheduled_on` và `effort`. `None` thành JSON null. Worker cũ không đi qua class này.

`MemoryPlanStore.add` lưu `priority` cùng cách. `replace` gán ưu tiên từ `Plan`, `None` là xóa, và áp `date_moves` với lý do cùng mốc do tool đưa. Danh sách dòng lịch sử nằm trên instance. Bộ chấm eval đọc danh sách đó.

Test kho đọc `subtask_date_moves` bằng PostgREST trong `tests/`. `src/` không thêm hàm đọc lịch sử cho mô hình. `empty_plan_tables` không xóa được bảng lịch sử. Assertion lọc theo `plan_id` và `subtask_id` của lần ghi, không đếm cả bảng.
