# Contract: Bộ định nghĩa sáu tool

Nguồn duy nhất: `src/tools/tool_definitions.py`. `src/tools/schemas.py` không được thêm schema đầu vào.

`DEFINITIONS_VERSION` là `int` và bằng `1`.

`TOOL_DEFINITIONS` có đúng sáu khóa, theo thứ tự dưới đây. Không có khóa nào khác.

## Mô tả

| Tên | `description` |
|-----|----------------|
| `create_plan` | `Tạo một kế hoạch mới từ mục tiêu và danh sách việc con.` |
| `get_plans` | `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu.` |
| `get_plan_detail` | `Mở một kế hoạch theo danh tính.` |
| `update_subtask` | `Đặt trạng thái một việc con thành pending, done hoặc skipped.` |
| `add_subtask` | `Thêm một việc con vào cuối một kế hoạch.` |
| `set_subtask_note` | `Đặt hoặc xóa ghi chú của một việc con.` |

## Schema đầu vào

Mọi schema có `type` là `object` và `additionalProperties` là `false`. Thứ tự khóa trong `properties` là thứ tự xét kiểu. Thứ tự `required` là thứ tự xét thiếu.

### create_plan

`required`: `goal`.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `goal` | string | có |
| `subtasks` | array của string | không |

### get_plans

`required`: rỗng.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `keyword` | string | không |

Object rỗng là hợp lệ.

### get_plan_detail

`required`: `plan_id`.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `plan_id` | string | có |

### update_subtask

`required`: `plan_id`, `subtask_id`, `status`.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `plan_id` | string | có |
| `subtask_id` | string | có |
| `status` | string | có |

`status` không khai `enum`.

### add_subtask

`required`: `plan_id`, `title`.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `plan_id` | string | có |
| `title` | string | có |

### set_subtask_note

`required`: `plan_id`, `subtask_id`, `note`.

| Trường | Kiểu | Bắt buộc |
|--------|------|----------|
| `plan_id` | string | có |
| `subtask_id` | string | có |
| `note` | string | có |

Bỏ `note` là thiếu trường. Chuỗi rỗng là đúng kiểu và đi vào tool.
