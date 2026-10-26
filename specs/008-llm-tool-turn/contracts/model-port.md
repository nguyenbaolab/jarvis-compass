# Contract: Cổng mô hình

File: `src/core/llm.py`. Chỉ thư viện chuẩn. Không import `anthropic`, `tools`, `db`, `fastapi`, `pydantic`.

## Kiểu

Các kiểu ở [data-model.md](../data-model.md): `TextMessage`, `ToolRequest`, `ToolResultMessage`, `ModelRequest`, `ModelResponse`, `ModelError`.

`ModelError` là `Exception`. Thuộc tính `class_name` là str. Thông điệp của exception là đúng `class_name`, không phải thông điệp SDK.

## Protocol

```text
model: str

async def complete(self, request: ModelRequest, *, api_key: str, timeout: float) -> ModelResponse
```

Protocol có thuộc tính `model`. Adapter đặt bằng `claude-haiku-5-5`. Client giả của test lượt cũng có thuộc tính này.

Tên phương thức là `complete`. Người gọi của cổng là `run_turn` hoặc test. Adapter và client giả đều có phương thức này.

`api_key` và `timeout` là keyword-only. Cổng không đọc môi trường tiến trình và không tự tính ngân sách.

## Lỗi

Exception của nhà cung cấp không đi ra khỏi adapter. Adapter đổi chúng thành `ModelError` trước khi `complete` trả về. `CancelledError` không bị đổi và không bị nuốt.

Cổng không gọi mạng. Không có hàm nào trong file này tạo client SDK.
