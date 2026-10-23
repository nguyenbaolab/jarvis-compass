# Contract: get_plan_detail

Tool F06. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## Hàm

```text
get_plan_detail(
    plan_id: str | None,
    *,
    store: PlanStore,
) -> ToolResult
```

`plan_id` bắt buộc phải được truyền. Giá trị `None` là danh tính thiếu.

`store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

## Thành công

Trả `ToolResult` với `success is True`. `output` là một object JSON, UTF-8, sinh bởi `PlanJson.model_dump_json(ensure_ascii=False)`.

Hình object là hình một kế hoạch ở [create-plan.md](../../001-create-list-plans/contracts/create-plan.md): đúng ba khóa `id`, `goal`, `subtasks`. Không bọc trong khóa `plans`. `subtasks` là mảng object `{"title": ...}`, đủ và đúng thứ tự đã lưu.

Trước khi đọc, `normalize_plan_id` trong `src/core/plans.py` xử lý `plan_id`. Hàm đó chỉ dùng thư viện chuẩn. Khi nó trả về chuỗi, `get_plan_detail` gọi `store.get` với chuỗi đó. `PlanStore.get(plan_id: str) -> Plan | None` trả về kế hoạch có `id` bằng đúng chuỗi này, hoặc `None`.

`id` trong JSON bằng `Plan.id` đã lưu, bằng chuỗi đã `strip`. `goal` và `subtasks` bằng giá trị đã lưu của kế hoạch đó, cùng giá trị khi kế hoạch ấy xuất hiện trong `get_plans`.

Hàm không thêm, không sửa, không xóa kế hoạch.

## Từ chối

Ném `ToolError`. Không trả `ToolResult`. Store giữ nguyên. Lỗi miền từ `normalize_plan_id` được lớp tool đổi thành `ToolError` và mang nguyên câu của lỗi miền. `store.get` trả `None` thì lớp tool ném `ToolError` với câu không có kế hoạch.

Hai câu, khác nhau từng ký tự:

| Tình huống | Câu của `ToolError` |
|------------|---------------------|
| `plan_id` là `None`, `""`, hoặc `plan_id.strip()` còn rỗng | `Danh tính kế hoạch chưa được đưa.` |
| `plan_id.strip()` còn nội dung nhưng không có `Plan.id` nào bằng chuỗi đó | `Không có kế hoạch với danh tính này.` |

`str.strip()` chỉ bỏ hai đầu. So phần còn lại bằng `==` với `Plan.id`, có phân biệt hoa thường. Không NFC, không `casefold`.

Ví dụ: id đã lưu là chữ thường. Cùng id viết hoa thì từ chối bằng câu "không có kế hoạch". Cùng id với khoảng trắng hai đầu thì thành công. Chuỗi là mục tiêu của một kế hoạch, mà chuỗi đó không bằng `id`, thì từ chối bằng câu "không có kế hoạch".

Sau một lần từ chối, `get_plans` trên cùng store trả cùng tập như trước lần từ chối, và `get_plan_detail` với đúng id đã lưu vẫn trả về kế hoạch đó.

## Ngoài hợp đồng

Hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Hàm không đọc hay ghi biến module. Hàm không đổi `create_plan` hay `get_plans`.
