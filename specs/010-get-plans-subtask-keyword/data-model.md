# Data Model: Từ khóa liệt kê khớp tiêu đề việc con

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách chọn hàm: [research.md](./research.md). Chữ ký và câu mô tả: [contracts/keyword-filter.md](./contracts/keyword-filter.md).

`Plan`, `Subtask`, và `SubtaskStatus` giữ trường và kiểu đã có trong `src/core/plans.py`. Lát này không thêm trường, không đổi kiểu, và không đổi nghĩa "có mặt trong store là đang hoạt động".

## Chỗ so khớp

| Chỗ | Có được xét |
|-----|-------------|
| `Plan.goal` | Có. Cùng luật chữ đang có. |
| `Subtask.title` | Có. Cùng luật chữ với mục tiêu. Mọi `SubtaskStatus`: `pending`, `done`, `skipped`. |
| `Subtask.note` | Không. |
| `Subtask.id`, `Plan.id` | Không. |

Một kế hoạch khớp được trả nguyên: cùng `id`, cùng `goal`, cùng tuple việc con, cùng trạng thái, cùng ghi chú, cùng thứ tự việc con. `created_order` vẫn không có trong JSON.

## Hàm miền

Nằm ở `src/core/plans.py`. Không gọi store. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

| Hàm | Việc phải làm |
|-----|----------------|
| `filter_by_keyword(plans: tuple[Plan, ...], keyword: str \| None) -> tuple[Plan, ...]` | Tên mới của hàm lọc duy nhất. `keyword` là `None`, hoặc NFC rồi `strip` còn rỗng: trả đúng `plans`. Ngược lại giữ những `Plan` có kim trong `goal` hoặc trong ít nhất một `title`. Mỗi `Plan` tối đa một lần. Thứ tự tương đối của `plans` giữ nguyên. |

Bước NFC rồi `casefold` là một hàm lồng trong `filter_by_keyword`. Hàm lồng không `strip`. Kim, `goal`, và mỗi `title` đi qua hàm lồng đó. `note` không đi qua.

`PlanStore` không thêm thao tác. Lát này chỉ đọc `list_newest_first` đã có. `add`, `get`, và `replace` không đổi.

## Bộ định nghĩa tool

Không có thực thể lưu mới. Hai giá trị của catalog đổi:

| Mục | Giá trị |
|-----|---------|
| `DEFINITIONS_VERSION` | Số nguyên `2` |
| `get_plans.description` | `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.` |
| `get_plans.input_schema` | Giữ nguyên |
