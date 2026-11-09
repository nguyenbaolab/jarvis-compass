# Catalog tool bản 3

Chín tool. `DEFINITIONS_VERSION` là số nguyên 3. Sáu tool đầu đang có. Ba tool sau là mới. Mỗi tool mới làm một việc.

Kiểm kiểu ở `tool_router` phải nhận `string`, `boolean`, `null`, `array` của chuỗi, và `array` của object. Object lồng có `additionalProperties: false` thì khóa lạ là lỗi đầu vào.

Dòng log tool và dòng log mô hình không thêm khóa. Chỉ số phiên bản đổi.

## `create_plan`

`goal` bắt buộc, chuỗi. `priority` không bắt buộc, `high`, `medium`, hoặc `low`. `subtasks` không bắt buộc. Khi có, đó là mảng object, không còn mảng chuỗi.

Mỗi phần tử:

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `title` | có | chuỗi |
| `scheduled_on` | không | chuỗi `YYYY-MM-DD` |
| `effort` | không | `S`, `M`, hoặc `L` |

`additionalProperties` của phần tử là false. Không kiểm trùng hạn. Không sinh dòng lịch sử. Ngày đặt ở đây không đi qua `reschedule_subtasks`. `priority` đi xuống `PlanStore.add`, rồi tham số `priority` của `add_plan`. Khóa vắng là ưu tiên trống, không phải mức vừa.

## `get_plans`

Giữ `keyword` chuỗi, không bắt buộc. JSON trả về dùng `PlanJson` đã thêm `priority`, `scheduled_on`, `effort`.

## `get_plan_detail`

Giữ `plan_id` chuỗi, bắt buộc. Cùng hình JSON với một phần tử của `get_plans`.

## `update_subtask`

Giữ `plan_id`, `subtask_id`, `status`. Không nhận ngày, sức, hay ưu tiên.

## `add_subtask`

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `plan_id` | có | chuỗi |
| `title` | có | chuỗi |
| `scheduled_on` | không | chuỗi `YYYY-MM-DD` |
| `effort` | không | `S`, `M`, hoặc `L` |

Không kiểm trùng. Không sinh dòng lịch sử.

## `set_subtask_note`

Giữ nguyên. Không nhận ngày, sức, hay ưu tiên.

## `set_plan_priority`

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `plan_id` | có | chuỗi |
| `priority` | có | `high`, `medium`, `low`, hoặc null |

Null là xóa ưu tiên. Lần ghi đi qua `replace`, và `plan_fields` luôn có khóa `priority`. JSON null xóa cột. Không đặt sức hay ngày. Không sinh dòng lịch sử.

## `set_subtask_effort`

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `plan_id` | có | chuỗi |
| `subtask_id` | có | chuỗi |
| `effort` | có | `S`, `M`, `L`, hoặc null |

Null là xóa sức. Không đặt ưu tiên hay ngày.

## `reschedule_subtasks`

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `plan_id` | có | chuỗi |
| `changes` | có | mảng object |
| `reason` | không | chuỗi |
| `confirm` | không | boolean |

Mỗi phần tử của `changes`:

| Khóa | Bắt buộc | Kiểu |
|---|---|---|
| `subtask_id` | có | chuỗi |
| `scheduled_on` | có | chuỗi `YYYY-MM-DD`, hoặc null |

`additionalProperties` false ở tool và ở từng phần tử. `confirm` vắng được hiểu là false.

Tool đọc `TurnContext` do `execute_tool` nhận. Không có ngữ cảnh thì lỗi tool, không đoán mốc, không ghi. `moved_at` là `instant` của ngữ cảnh đó.

Một lần gọi là một lần ghi khi được ghi. Việc đổi từ một ngày sang một ngày khác có một dòng lịch sử trong lần ghi đó. Việc từ trống sang ngày, hoặc từ ngày sang trống, đổi ngày đã lưu và không có dòng. Lần ghi này cũng gửi `plan.priority` trong `plan_fields`, nên ưu tiên đang có không bị xóa chỉ vì dời ngày.

Trùng chỉ khi hạn của kế hoạch này sau lần dời, theo FR-005, bằng hạn một kế hoạch khác. Lần dời không đổi hạn của chính kế hoạch thì ghi ngay, không cần `confirm`.

Khi trùng và `confirm` không phải true: kết quả thành công, không ghi, chữ cho mô hình nói kế hoạch kia và hạn. `effect` là null. Không vào bản ghép D-021. Tool đặt `clash_reported` trên ngữ cảnh của lượt. `run_turn` không đọc chữ này và không biết tên tool.

Khi trùng, `confirm` là true, và `clash_reported` đã đặt trong cùng ngữ cảnh: lỗi tool, không ghi.

Khi trùng, `confirm` là true, và cờ chưa đặt: ghi. Cờ không chứng minh chủ bot đã đồng ý. Lượt sau là một `run_turn` mới, cờ bắt đầu bằng false.

Không cộng giờ. Không áp quỹ 8 giờ.
