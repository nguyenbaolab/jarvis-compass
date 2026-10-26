# Quickstart: Lượt trả lời có gọi mô hình

Kiểm lát này không mở mạng và không cần khóa thật. Không sửa assertion của test cũ.

## Trước khi chạy

Từ gốc repo:

```text
uv sync
```

Không thêm dependency. `anthropic` đã có trong `pyproject.toml`.

## Hai file mới

Viết test trước mã. Lần chạy đầu, khi mã chưa có, pytest phải fail. In output đó trong phiên implement, rồi mới viết `src/`.

```text
uv run pytest tests/test_llm_turn.py tests/test_anthropic_model.py --tb=short
```

Kỳ vọng sau khi mã xong: cả hai file pass, exit code 0. Không có dòng skipped.

`tests/test_llm_turn.py` dùng client giả trả danh sách `ModelResponse` hoặc ném lỗi. Không import `anthropic`. Năm hàm riêng:

- bốn phản hồi liên tiếp đều đòi tool: ba vòng chạy, phản hồi thứ tư không gọi `execute_tool` và không gọi `complete` thêm, kết quả đúng `Chưa trả lời xong yêu cầu này.`
- khóa `None` và khóa `""`: exception đúng `Thiếu ANTHROPIC_API_KEY.`, client giả không được gọi, kể cả khi môi trường tiến trình có khóa khác
- đồng hồ bịt làm lượt vượt 20 giây trước lần gọi tiếp: kết quả là câu lỗi phía mô hình, không có `complete` sau mốc đó
- client giả ném `CancelledError`: lỗi đó đi ra, không thành hai câu trả lời
- client giả ném lỗi có `secret-key-value`, `http://example.invalid`, và `429` trong thông điệp: kết quả đúng câu lỗi phía mô hình và không chứa ba mảnh đó

Đồng hồ của các ca ngân sách bịt `turns.llm_turn._now`. Không bịt `time.monotonic`.

`tests/test_anthropic_model.py` thay `AsyncAnthropic` bằng lớp giả dùng được trong `async with`, và đọc đối số đã ghi. Không đọc attribute riêng của adapter. Không mở socket. Một ca: một vòng hai tool, một kết quả `is_error` true. `messages` gồm lịch sử văn bản, một tin assistant với hai khối `tool_use` đúng thứ tự, rồi một tin user với hai khối `tool_result` đúng `tool_use_id`, `content` và `is_error`.

## Cả bộ

Khi Supabase local đang chạy và `JARVIS_TEST_SUPABASE_URL` cùng `JARVIS_TEST_SUPABASE_KEY` đã đặt trong tiến trình:

```text
uv run pytest -rs
```

Kỳ vọng exit code 0 và không có skipped. Lệnh này không phải điều kiện của hai file mới, vì hai file đó không đụng kho.

## Việc không chạy trong pytest

Gọi API Anthropic thật, nếu có, là việc tay. Không thêm ca đó vào `tests/`.
