# Contract: add_subtask

Tool F08. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## Hàm

```text
add_subtask(
    plan_id: str | None,
    title: str | None,
    *,
    store: PlanStore,
) -> ToolResult
```

Hai đối số đầu bắt buộc phải được truyền. Giá trị `None` là phần đó thiếu. Hàm không nhận trạng thái và không nhận danh sách tiêu đề.

`store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

## Thành công

Trả `ToolResult` với `success is True`. `output` là một object JSON, UTF-8, sinh bởi `_plan_json` rồi `PlanJson.model_dump_json(ensure_ascii=False)`. `_plan_json` là đúng hàm `get_plan_detail` đang dùng. Không có hàm dựng JSON thứ hai. Không bọc trong khóa `plans`.

Trước `store.get`, theo đúng thứ tự:

1. `normalize_plan_id(plan_id)`
2. `new_subtask(title)`

Cả hai nằm ở `src/core/plans.py` và chỉ dùng thư viện chuẩn. `new_subtask` là hàm duy nhất chuẩn hóa tiêu đề, từ chối tiêu đề thiếu hoặc rỗng, cấp `id`, và gán `SubtaskStatus.PENDING`. `normalize_new_plan` gọi cùng hàm đó cho từng tiêu đề. Khi cả hai trả về, hàm gọi `store.get` với danh tính kế hoạch đã `strip`. `get` trả về `Plan` thì `append_subtask` nhận `Plan` đó và `Subtask` vừa dựng. Tool gọi `store.replace` với `Plan` mà `append_subtask` trả về.

JSON trả về là kế hoạch sau `replace`: cùng `id` kế hoạch, cùng `goal`, số việc con cũ cộng một, cùng thứ tự các việc cũ, cùng `id`, `title`, và `status` của từng việc cũ. Việc mới đứng cuối, `status` là `"pending"`, `title` là dạng đã chuẩn hóa. `created_order` không có trong JSON và không đổi trên `Plan` được ghi.

`PlanStore` không thêm phương thức. Hàm không gọi `store.add`.

## Từ chối

Ném `ToolError`. Không trả `ToolResult`. Store giữ nguyên: không `replace`, không `add`. Lỗi miền đổi thành `ToolError` và mang nguyên câu của lỗi miền. Hàm dừng ở câu đầu tiên.

| Thứ tự | Tình huống | Câu của `ToolError` |
|--------|------------|---------------------|
| 1 | `plan_id` là `None`, `""`, hoặc `plan_id.strip()` còn rỗng | `Danh tính kế hoạch chưa được đưa.` |
| 2 | `title` là `None`, `""`, hoặc `_nfc_strip(title)` còn rỗng | `Việc con không được để trống.` |
| 3 | Danh tính kế hoạch còn nội dung nhưng `store.get` trả `None` | `Không có kế hoạch với danh tính này.` |

Hàng 1 là câu của `normalize_plan_id`, cùng câu với `update_subtask`. Hàng 2 là câu của `new_subtask`, cùng câu tạo kế hoạch đang dùng cho việc con trống. Hàng 3 là câu lớp tool đã dùng khi `get` trả `None` ở `update_subtask`.

`str.strip()` của danh tính chỉ bỏ hai đầu. So danh tính bằng `==`, có phân biệt hoa thường. Không NFC, không `casefold`. Tiêu đề đi qua NFC rồi `strip`. Khoảng trắng đôi bên trong tiêu đề được giữ.

Hàng 2 xảy ra cả khi danh tính kế hoạch không trùng kế hoạch nào. Hàng 3 chỉ xảy ra khi hàng 1 và hàng 2 đã qua. `new_subtask` có thể đã tạo một `Subtask` chưa được `replace` khi hàng 3 xảy ra. Object đó không vào store.

Sau một lần từ chối, `get_plans` trên cùng store trả cùng tập như trước lần từ chối. Một lần thêm sau bằng dữ liệu đúng vẫn trả về `ToolResult`.

`create_plan` với một phần tử tiêu đề `None` cũng ném `ToolError` câu hàng 2 và không gọi `store.add`, vì `normalize_new_plan` gọi `new_subtask`. Các test cũ của `create_plan` không truyền `None` và không bị sửa assertion.

## Ngoài hợp đồng

Hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Hàm không đọc hay ghi biến module. Hàm không sửa `Plan`, `Subtask`, hay `SubtaskStatus`. Hàm không chèn vào vị trí người gọi chọn, không xóa, không sắp xếp lại, không sửa tiêu đề việc đã có, và không đổi trạng thái việc đã có. Hàm không thêm nhiều việc con trong một lần gọi.
