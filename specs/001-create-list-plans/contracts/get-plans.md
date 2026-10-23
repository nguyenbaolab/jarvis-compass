# Contract: get_plans

Tool F05. Người gọi trong lát cắt này là test. Router LLM và route HTTP nằm ngoài phạm vi, xem [spec.md](../spec.md).

## Hàm

```text
get_plans(
    keyword: str | None = None,
    *,
    store: PlanStore,
) -> ToolResult
```

`store` là tham số keyword-only và bắt buộc. Hàm không có store mặc định.

## Thành công

Luôn trả `ToolResult` với `success is True`, kể cả khi không có kế hoạch khớp. `output` là một object JSON, UTF-8, sinh bởi Pydantic `model_dump_json(ensure_ascii=False)`.

```json
{
  "plans": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "goal": "Học tiếng Nhật",
      "subtasks": [
        {"title": "Học hiragana"},
        {"title": "Luyện 10 phút mỗi ngày"}
      ]
    }
  ]
}
```

| Trường | Quy tắc |
|--------|---------|
| `plans` | Mảng, luôn có mặt. Rỗng khi store rỗng hoặc không kế hoạch nào khớp. |
| Mỗi phần tử | Cùng hình `id`, `goal`, `subtasks` như [create-plan.md](./create-plan.md). `id` và `goal` đúng giá trị đã lưu. `subtasks` là mảng object `{"title": "..."}`, đủ và đúng thứ tự đã lưu. |

Không lọc (`keyword` bỏ qua, `None`, `""`, hoặc chỉ khoảng trắng sau NFC rồi `strip`): mọi kế hoạch trong store, kế hoạch có `created_order` lớn hơn đứng trước.

Có lọc: giữ tập con của danh sách đó. Từ khóa đi qua `unicodedata.normalize("NFC", ...)` rồi `str.strip()`. So khớp: NFC rồi `casefold` ở cả hai phía. Một kế hoạch được giữ khi từ khóa đã chuẩn hóa, sau `casefold`, là đoạn con của `goal` sau NFC rồi `casefold`. Việc con không được xét. Thứ tự tương đối của danh sách không lọc được giữ. `"tieng"` không khớp `"tiếng"`.

Store rỗng hoặc không khớp trả `{"plans": []}`, không ném lỗi.

## Chuẩn hóa Unicode

Giá trị `goal` đã lưu là dạng NFC. Chữ "ế" trong "tiếng": NFC là U+1EBF; NFD là U+0065 U+0302 U+0301.

Hai tình huống kiểm:

- (a) Tạo với `goal` là `unicodedata.normalize("NFD", "Học tiếng Nhật")`. `get_plans` không lọc trả về `goal` là `unicodedata.normalize("NFC", "Học tiếng Nhật")`.
- (b) Goal đã lưu từ dạng NFD ở tình huống (a). `get_plans` với `keyword` là `unicodedata.normalize("NFC", "tiếng")` trả về kế hoạch đó.

## Ngoài hợp đồng

Hàm không gọi LLM, HTTP, Telegram, hay PostgREST. Hàm không thêm, sửa, hay xóa kế hoạch. Hàm không đọc hay ghi biến module.
