# Contract: update_subtask

Tool F07. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## Hàm

```text
update_subtask(
    plan_id: str | None,
    subtask_id: str | None,
    status: str | None,
    *,
    store: PlanStore,
) -> ToolResult
```

Ba đối số đầu bắt buộc phải được truyền. Giá trị `None` là phần đó thiếu.

`store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

## Hình việc con dùng chung

`create_plan`, `get_plans`, `get_plan_detail`, và `update_subtask` xuất mỗi việc con bằng `SubtaskJson` với đúng ba khóa, theo thứ tự:

| Khóa | Quy tắc |
|------|---------|
| `id` | `str(uuid.uuid4())` đã cấp lúc tạo. Giữ nguyên sau cập nhật trạng thái. |
| `title` | Nội dung đã lưu. Cùng luật NFC rồi `strip` ở [create-plan.md](../../001-create-list-plans/contracts/create-plan.md). Cập nhật trạng thái không đổi khóa này. |
| `status` | JSON xuất chuỗi `"pending"` hoặc `"done"`. `SubtaskJson.status` khai báo đúng hai giá trị đó. Lúc tạo là `"pending"`. Sau cập nhật thành công là chuỗi của `SubtaskStatus` vừa đặt. |

`PlanJson` vẫn đúng ba khóa `id`, `goal`, `subtasks`. `created_order` không có trong JSON. Việc con mới tạo có `status` là `pending` trong kết quả tạo, liệt kê, và mở.

## Thành công

Trả `ToolResult` với `success is True`. `output` là một object JSON, UTF-8, sinh bởi `PlanJson.model_dump_json(ensure_ascii=False)`. Không bọc trong khóa `plans`.

Trước `store.get`, theo đúng thứ tự:

1. `normalize_plan_id(plan_id)`
2. `normalize_subtask_id(subtask_id)`
3. `normalize_subtask_status(status)`

Cả ba nằm ở `src/core/plans.py` và chỉ dùng thư viện chuẩn. Hai hàm danh tính trả về chuỗi. `normalize_subtask_status` trả về `SubtaskStatus`. Khi cả ba trả về, hàm gọi `store.get` với danh tính kế hoạch đã `strip`. `get` trả về `Plan` thì `replace_subtask_status` nhận `SubtaskStatus` đó. Nếu hàm đó trả về object `Plan` khác, tool gọi `store.replace` với object đó. Nếu trả về đúng object cũ, tool không gọi `replace`.

JSON trả về là kế hoạch sau bước đó: cùng `id` kế hoạch, cùng `goal`, cùng số việc con, cùng thứ tự, cùng `id` và `title` của từng việc. Đúng một việc, việc có `id` đã yêu cầu, có `status` vừa đặt. Các việc khác giữ `status`.

Đặt lại đúng `status` đang có vẫn là thành công. JSON vẫn là kế hoạch đó. Store không bị `replace`.

## Từ chối

Ném `ToolError`. Không trả `ToolResult`. Store giữ nguyên. Lỗi miền đổi thành `ToolError` và mang nguyên câu của lỗi miền. Hàm dừng ở câu đầu tiên.

| Thứ tự | Tình huống | Câu của `ToolError` |
|--------|------------|---------------------|
| 1 | `plan_id` là `None`, `""`, hoặc `plan_id.strip()` còn rỗng | `Danh tính kế hoạch chưa được đưa.` |
| 2 | `subtask_id` là `None`, `""`, hoặc `subtask_id.strip()` còn rỗng | `Danh tính việc con chưa được đưa.` |
| 3 | `status` là `None`, `""`, `status.strip()` còn rỗng, hoặc phần còn lại không phải `pending` hay `done` | `Trạng thái việc con chỉ nhận pending hoặc done.` |
| 4 | Danh tính kế hoạch còn nội dung nhưng `store.get` trả `None` | `Không có kế hoạch với danh tính này.` |
| 5 | Kế hoạch tìm thấy không có việc con với `id` bằng danh tính việc con đã `strip` | `Kế hoạch này không có việc con với danh tính này.` |

`str.strip()` chỉ bỏ hai đầu. So danh tính bằng `==`, có phân biệt hoa thường. Không NFC, không `casefold`. `pending` và `done` cũng so từng ký tự sau `strip`. `Done`, `PENDING`, `xong`, và `chưa xong` rơi vào hàng 3.

Hàng 2 xảy ra cả khi danh tính kế hoạch không trùng kế hoạch nào. Hàng 3 xảy ra cả khi kế hoạch không tồn tại hoặc việc con không thuộc kế hoạch. Hàng 4 chỉ xảy ra khi hàng 1 đến 3 đã qua. Hàng 5 chỉ xảy ra khi hàng 1 đến 4 đã qua. Danh tính việc con của kế hoạch khác, tiêu đề, hoặc vị trí trong danh sách, khi chuỗi đó không phải `id` đã cấp, là hàng 5. Kế hoạch kia không bị `replace`.

Sau một lần từ chối, `get_plans` trên cùng store trả cùng tập như trước lần từ chối. Một lần cập nhật sau bằng dữ liệu đúng vẫn trả về `ToolResult`.

## Ngoài hợp đồng

Hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Hàm không đọc hay ghi biến module. Hàm không sửa `title`, không thêm, không xóa, không sắp xếp lại việc con. Hàm không đưa kế hoạch ra khỏi store khi mọi việc con là `done`. Hàm không nhận `skipped`.
