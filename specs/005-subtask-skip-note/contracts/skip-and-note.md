# Contract: Bỏ qua việc con và ghi chú

Phần còn lại của tool F07, cộng tool đặt ghi chú. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## JSON việc con

Mọi tool trả kế hoạch qua `_plan_json`: `create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, `add_subtask`, và `set_subtask_note`.

Mỗi phần tử `subtasks` có đúng bốn khóa, theo thứ tự: `id`, `title`, `status`, `note`.

| Khóa | Giá trị |
|------|---------|
| `status` | `"pending"`, `"done"`, hoặc `"skipped"` |
| `note` | chuỗi đã lưu, hoặc `null` |

`note` luôn có mặt. Không cấu hình lược trường `null`. Việc con mới có `note` là `null` và `status` là `"pending"`.

## update_subtask

Chữ ký và thứ tự kiểm giữ như [contract cập nhật việc con](../../003-update-subtask/contracts/update-subtask.md), với một thay đổi ở hàng trạng thái.

| Thứ tự | Tình huống | Câu của `ToolError` |
|--------|------------|---------------------|
| 3 | `status` là `None`, `""`, `status.strip()` còn rỗng, hoặc phần còn lại không phải `pending`, `done`, hay `skipped` | `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` |

`skipped` đi được từ và tới `pending` và `done`. `" skipped "` là `skipped`. `Skipped`, `SKIPPED`, và `bỏ qua` bị từ chối bằng câu trên, kể cả khi không có kế hoạch đó.

Một lần thành công chỉ đổi `status` của đúng việc. `note` của việc đó giữ nguyên. Đặt lại đúng trạng thái đang có thành công và không gọi `store.replace`.

Các câu danh tính và câu không có kế hoạch giữ nguyên.

## set_subtask_note

```text
set_subtask_note(
    plan_id: str | None,
    subtask_id: str | None,
    note: str | None,
    *,
    store: PlanStore,
) -> ToolResult
```

Ba đối số đầu bắt buộc phải được truyền. Giá trị `None` là phần đó thiếu. `store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

### Thành công

Trả `ToolResult` với `success is True`. `output` do `_plan_tool_result`, cùng đường với `update_subtask`.

Trước `store.get`, theo đúng thứ tự:

1. `normalize_plan_id(plan_id)`
2. `normalize_subtask_id(subtask_id)`
3. `normalize_subtask_note(note)`

Bước 3 không ném lỗi. `None`, `""`, hoặc `_nfc_strip` còn rỗng thành `None`. Chuỗi còn nội dung là NFC rồi bỏ khoảng trắng hai đầu. Không cắt.

`store.get` trả `Plan` thì `replace_subtask_note` nhận kế hoạch đó, danh tính việc con đã `strip`, và ghi chú đã chuẩn hóa. Object trả về khác object đã đọc thì `store.replace`. Cùng object thì không gọi `replace`.

JSON là kế hoạch sau thao tác. Đúng một việc đổi `note`. `status`, `title`, và `id` của việc đó giữ nguyên. Các việc khác giữ nguyên.

Đặt lại đúng ghi chú đang có, sau chuẩn hóa, thành công và không gọi `replace`. Xóa khi `note` đang là `None` cũng không gọi `replace`.

### Từ chối

Ném `ToolError`. Không trả `ToolResult`. Store giữ nguyên: không `replace`. Hàm dừng ở câu đầu tiên.

| Thứ tự | Tình huống | Câu của `ToolError` |
|--------|------------|---------------------|
| 1 | `plan_id` là `None`, `""`, hoặc `plan_id.strip()` còn rỗng | `Danh tính kế hoạch chưa được đưa.` |
| 2 | Danh tính kế hoạch còn nội dung, `subtask_id` là `None`, `""`, hoặc `subtask_id.strip()` còn rỗng | `Danh tính việc con chưa được đưa.` |
| 3 | Hai danh tính còn nội dung nhưng `store.get` trả `None` | `Không có kế hoạch với danh tính này.` |
| 4 | Kế hoạch có thật nhưng không có việc con với danh tính đã `strip` | `Kế hoạch này không có việc con với danh tính này.` |

Hàng 1 và 2 là câu của `normalize_plan_id` và `normalize_subtask_id`. Hàng 3 là `_MISSING_PLAN_MESSAGE`. Hàng 4 là hằng duy nhất trong `src/core/plans.py`, cùng hằng `replace_subtask_status` đang dùng. Không có bản sao của vòng tìm theo `id`.

Ghi chú `None` hoặc chỉ khoảng trắng trên một danh tính kế hoạch không tồn tại vẫn là hàng 3. Ghi chú đó không phải lỗi.

So danh tính bằng `==` sau `strip`, có phân biệt hoa thường. Không NFC và không `casefold` cho danh tính.

Sau một lần từ chối, `get_plans` trên cùng store trả cùng tập như trước lần từ chối. Một lần đặt sau bằng dữ liệu đúng vẫn trả về `ToolResult`.

## Ngoài hợp đồng

Hai hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Không đọc hay ghi biến module. Không thêm phương thức `PlanStore`. Không xóa việc con, không sửa tiêu đề, không lưu lịch sử ghi chú, và không đặt trạng thái cho cả kế hoạch.
