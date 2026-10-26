# Contract: execute_tool

Router: `src/tools/tool_router.py`. Catalog: [tool-definitions.md](./tool-definitions.md). Kho do người gọi đưa. Router không import `db`.

## Chữ ký

```text
async def execute_tool(
    name: object,
    tool_input: object,
    *,
    store: PlanStore,
    log: Callable[[str], None] | None = None,
) -> ToolResult
```

`store` là keyword-only. `log` là keyword-only. `log` là `None` thì ghi bằng `print(line, flush=True)`. Test truyền một hàm nhận đúng một `str`.

Trả `ToolResult`. `success` sai là cờ lỗi. `output` là nội dung gửi lại mô hình. Hàm không ném `Exception`.

Gọi tool sau khi đầu vào hợp lệ:

| Tên | Lời gọi |
|-----|---------|
| `create_plan` | `create_plan(goal, subtasks=..., store=store)` — bỏ `subtasks` khi khóa không có |
| `get_plans` | `get_plans(keyword=..., store=store)` — bỏ `keyword` khi khóa không có |
| `get_plan_detail` | `get_plan_detail(plan_id, store=store)` |
| `update_subtask` | `update_subtask(plan_id, subtask_id, status, store=store)` |
| `add_subtask` | `add_subtask(plan_id, title, store=store)` |
| `set_subtask_note` | `set_subtask_note(plan_id, subtask_id, note, store=store)` |

Không đổi chữ ký sáu hàm đó. Bảng tên trong router bằng đúng tập khóa của catalog.

## Câu lỗi do lớp này viết

| Tình huống | `output` | `error_type` |
|------------|----------|----------------|
| Tên không có trong catalog, kể cả `revise_plan`, `Create_plan`, và chuỗi rỗng | `Không có tool với tên này.` | `unknown_tool` |
| Đầu vào không phải `dict` | `Đầu vào phải là một object.` | `invalid_input` |
| Thiếu trường bắt buộc | `Đầu vào thiếu trường <tên>.` | `invalid_input` |
| Thừa trường | `Đầu vào thừa trường <tên>.` | `invalid_input` |
| Sai kiểu cả trường | `Trường <tên> sai kiểu.` | `invalid_input` |
| Phần tử mảng không phải chuỗi | `Một phần tử của trường <tên> sai kiểu.` | `invalid_input` |
| `Exception` không phải `ToolError` hay `PlanDomainError` | `Không thực hiện được yêu cầu này.` | `unexpected` |

`<tên>` là tên trường, không thêm dấu nháy. Một lần chỉ một câu, theo thứ tự trong [data-model.md](../data-model.md).

`ToolError` và `PlanDomainError`: `output` bằng `str(error)`, `error_type` là `domain`. Không sửa chữ.

Ca tối thiểu, mỗi ca `success` là `False` và kho không bị gọi:

| Tool | Sai kiểu | Thiếu hoặc thay thế |
|------|----------|---------------------|
| `create_plan` | `subtasks` là `["Học hiragana", null]` → câu phần tử | thiếu `goal` |
| `get_plans` | `keyword` là số | thừa `limit`. Không có ca thiếu trường |
| `get_plan_detail` | `plan_id` là số | thiếu `plan_id` |
| `update_subtask` | `status` là số | thiếu `status` |
| `add_subtask` | `title` là số | thiếu `title` |
| `set_subtask_note` | `note` là số | thiếu `note` |

`update_subtask` với object thiếu `status` và có thêm `limit`: câu là `Đầu vào thừa trường limit.`

`create_plan` với `goal` là `""`: `domain`, câu `Mục tiêu không được để trống.`

`get_plan_detail` với `plan_id` là `"khong-co"` trên kho trống: `domain`, câu `Không có kế hoạch với danh tính này.`

Kho `get` ném `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")`: `output` đúng câu đó.

Kho ném `RuntimeError` có thông điệp chứa `secret-key-value`: `output` là câu chung, không chứa chuỗi đó, không chứa `RuntimeError`.

`KeyboardInterrupt` từ kho đi ra khỏi `execute_tool`. Không đổi thành `ToolResult`.

## Log

Mỗi lần trả `ToolResult` gọi `log` đúng một lần. Đối số là một dòng, không có ký tự xuống dòng bên trong. `json.loads` đọc được. `json.dumps` dùng `ensure_ascii=False`: chuỗi `Học tiếng Nhật` xuất hiện nguyên trong dòng.

Bảy khóa, đúng thứ tự ghi trong [data-model.md](../data-model.md). `definitions_version` là số `1`. `duration_ms` là số nguyên `>= 0`. Test được bịt `time.monotonic` để thấy một khoảng đã chọn đổi thành số mili giây làm tròn xuống. Test không đòi lớn hơn 0.

`unexpected`: `detail` đúng bằng tên lớp, ví dụ `RuntimeError`. Dòng không chứa thông điệp exception. Các loại khác: `detail` là `null`.

Một lần gọi trên kho trong bộ nhớ, khi không bịt đồng hồ, có `duration_ms` nhỏ hơn 3000. Đây là kiểm ngân sách của lát này, không gồm lời gọi mô hình.

Đạt: `ok` là `true`, `error_type` là `null`, `detail` là `null`, `output` của `ToolResult` trùng `output` mà cùng tool trả trên cùng kho và cùng đầu vào. So trên `get_plans` sau khi kho đã có dữ liệu, vì lần đó không cấp danh tính mới.

Ca tên lạ và ca đầu vào sai không gọi phương thức kho.
