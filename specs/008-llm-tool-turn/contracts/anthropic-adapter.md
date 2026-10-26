# Contract: Adapter Anthropic

File: `src/clients/anthropic_model.py`. Đây là chỗ duy nhất của lát này import `anthropic`.

## Hàm

Một lớp có thuộc tính `model: str` bằng `claude-haiku-5-5`, và `complete(self, request, *, api_key: str, timeout: float)`. Mỗi lần `complete` mở client rồi đóng kết nối:

```text
async with AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0) as client:
    ...
```

Không bỏ `api_key`, vì bỏ thì SDK tự đọc môi trường. Không tái dùng client của lần gọi trước, vì `timeout` là phần ngân sách còn lại của lần đó, và kết nối đóng khi hết khối `async with`.

Rồi `await client.messages.create` với các đối số:

| Đối số | Giá trị |
|--------|---------|
| model | `claude-haiku-5-5` |
| max_tokens | `2048` |
| thinking | `{"type": "disabled"}` |
| system | `request.system` |
| tools | mỗi mục của `request.tools`: `name`, `description`, `input_schema` lấy từ `TOOL_DEFINITIONS` |
| messages | lịch sử văn bản, rồi mỗi vòng đã chạy: một tin assistant chứa các khối tool, rồi một tin user chứa các khối kết quả theo cùng thứ tự |

Không truyền `stream`. Không truyền model nào khác.

## Dịch phản hồi

- Văn bản là phần text của content, nối theo thứ tự khối text.
- `stop_reason`, `usage.input_tokens`, `usage.output_tokens`, và `model` đưa vào `ModelResponse`. Thiếu token thì trường đó trống.
- Chỉ khi `stop_reason` là `tool_use`: mỗi khối `tool_use` có `id` str, `name` str, và `input` dict thành một `ToolRequest`. Khối khác bỏ qua.
- `stop_reason` khác `tool_use`: `tool_requests` rỗng, dù content có khối tool.

## Lỗi

Mọi `Exception` khi vào `async with`, khi `messages.create`, hoặc khi đóng client thành:

```text
raise ModelError(type(error).__name__) from None
```

Không gắn thông điệp SDK vào `ModelError`. `CancelledError` không nằm trong `Exception` của Python 3.13, nên nó đi tiếp mà không vào nhánh này.

## Test được phép nhìn

Test thay `AsyncAnthropic` ở chỗ adapter gọi, bằng một lớp giả dùng được trong `async with`. `__aenter__` trả đúng đối tượng có `messages.create`. Lớp giả ghi `kwargs` của constructor và `kwargs` của `messages.create`. Assertion đọc hai bản ghi đó.

Assertion bắt buộc: `model` là `claude-haiku-5-5`, `thinking` là `{"type": "disabled"}`, `api_key` là khóa đưa vào `complete`, `max_retries` là `0`.

Một ca nữa: một yêu cầu có một vòng gồm hai tool, và một kết quả có `is_error` true. `messages` gửi SDK gồm lịch sử văn bản, rồi một tin assistant có hai khối `tool_use` đúng `id`, `name`, `input` theo thứ tự, rồi một tin user có hai khối `tool_result` đúng `tool_use_id`, `content` và `is_error` theo cùng thứ tự.

Không đọc attribute của instance adapter.
