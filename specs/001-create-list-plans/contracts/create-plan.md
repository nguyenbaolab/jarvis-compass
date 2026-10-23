# Contract: create_plan

Tool F04. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## Hàm

```text
create_plan(
    goal: str | None,
    subtasks: list[str] | None = None,
    *,
    store: PlanStore,
) -> ToolResult
```

`store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

`goal` bắt buộc phải được truyền. Giá trị `None` là mục tiêu thiếu.

`subtasks` là danh sách chuỗi. Object chỉ xuất hiện trong JSON trả về, không phải trong đầu vào.

## Thành công

Trả `ToolResult` với `success is True`. `output` là một object JSON, UTF-8, sinh bởi Pydantic `model_dump_json(ensure_ascii=False)`.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "goal": "Học tiếng Nhật",
  "subtasks": [
    {"title": "Học hiragana"},
    {"title": "Luyện 10 phút mỗi ngày"}
  ]
}
```

| Trường | Quy tắc |
|--------|---------|
| `id` | Khớp `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`. Giữ nguyên ở lần `get_plans` sau trên cùng store. |
| `goal` | Mục tiêu sau `unicodedata.normalize("NFC", ...)` rồi `str.strip()`. Giá trị trả về là dạng NFC đã lưu. |
| `subtasks` | Mảng object, luôn có mặt, giữ thứ tự đầu vào. Rỗng khi đầu vào bỏ qua hoặc là mảng rỗng. Mỗi phần tử đúng một khóa `"title"`. `title` là chuỗi đầu vào sau NFC rồi `strip`. |

Đúng ba khóa ở object kế hoạch: `id`, `goal`, `subtasks`. Người kiểm tra parse JSON rồi so trường, không so nguyên văn chuỗi `output`.

Mỗi lần thành công thêm đúng một kế hoạch vào `store`, kể cả khi mục tiêu và việc con trùng một kế hoạch đã có.

## Chuẩn hóa Unicode

`goal` và từng chuỗi việc con đi qua `unicodedata.normalize("NFC", ...)` rồi `str.strip()` trước khi lưu. Giá trị lưu và giá trị trong JSON là dạng NFC. Dấu không bị bỏ: `"tieng"` không khớp `"tiếng"`. Chữ "ế" trong "tiếng": NFC là U+1EBF; NFD là U+0065 U+0302 U+0301.

Hai tình huống kiểm:

- (a) Tạo với `goal` là `unicodedata.normalize("NFD", "Học tiếng Nhật")`. `get_plans` không lọc trả về `goal` là `unicodedata.normalize("NFC", "Học tiếng Nhật")`. `create_plan` cũng trả về cùng `goal` NFC đó.
- (b) Goal đã lưu từ dạng NFD ở tình huống (a). `get_plans` với `keyword` là `unicodedata.normalize("NFC", "tiếng")` trả về kế hoạch đó.

## Từ chối

Ném `ToolError`. Không trả `ToolResult`. Không gọi `store.add`. Store giữ nguyên. Lỗi miền từ chuẩn hóa được lớp tool đổi thành `ToolError`.

Kiểm tra rỗng áp trên chuỗi đã NFC rồi `strip`. Các đầu vào bị từ chối:

- `goal` là `None`, `""`, hoặc chỉ khoảng trắng.
- Bất kỳ phần tử `subtasks` nào là `""` hoặc chỉ khoảng trắng, kể cả khi đứng giữa các phần tử hợp lệ.

Lời nhắn của `ToolError` là tiếng Việt, không nêu tên một nhân vật AI. Nội dung câu chữ không thuộc hợp đồng kiểm tra; điều phải quan sát là kiểu ngoại lệ và store không đổi.

## Ngoài hợp đồng

Hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Hàm không đọc hay ghi biến module.
