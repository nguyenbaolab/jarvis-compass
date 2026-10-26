# Research: Lượt trả lời có gọi mô hình

## 1. Đã thấy trong code

- `src/core/llm.py` chỉ có docstring `Claude API client wrapper, model-agnostic layer (F12).`
- `execute_tool(name, tool_input, *, store, log=None)` là `async def` và trả `ToolResult(success, output)`.
- `tool_router._now` trả `time.monotonic()`. Test router bịt `tools.tool_router._now`. Bịt `time.monotonic` toàn tiến trình làm hỏng vòng `asyncio` trên Windows.
- `check.ps1` fail khi `src/core` import `fastapi`, `pydantic`, `tools`, hoặc `db`.
- D-011: tools import core; core không import tools hay db.
- `pyproject.toml` dòng dependencies có `anthropic`. Bản đang cài là 1.5.0.
- `git grep -n ANTHROPIC_API_KEY -- src/config/settings.py` in đúng một dòng, dòng khai báo `ANTHROPIC_API_KEY: str = _get_str(...)`. `git grep` trên `*.py` không có chỗ thứ hai. Test không nhắc tên này.
- D-002: nhân vật duy nhất là JARVIS. Không có Friday hay tên khác.
- `TOOL_DEFINITIONS` là dict tên tới `description` và `input_schema`. `DEFINITIONS_VERSION` là int `1`.
- `StopReason` của SDK: `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`, `refusal`, `model_context_window_exceeded`.
- `AsyncAnthropic(api_key, timeout, max_retries=2)`. `messages.create` cần `max_tokens`. Tắt suy nghĩ bằng `thinking={"type": "disabled"}`.

## 2. Chỗ đặt và import

**Decision:** Cổng ở `src/core/llm.py`. Prompt ở `src/core/system_prompt.py`. Vòng lặp ở `src/turns/llm_turn.py`. Adapter ở `src/clients/anthropic_model.py`.

**Rationale:** Vòng lặp phải gọi `execute_tool`. Đặt nó trong `src/core` thì core import `tools`, và `check.ps1` cùng D-011 cấm điều đó. `src/clients` đã là kênh ngoài; adapter gọi SDK nên ở đó. Vòng lặp không phải kênh và không phải tool, nên ở gói `src/turns` dưới `src/`.

**Alternatives considered:** Đặt vòng lặp trong `src/core/llm.py` bị cấm bởi luật import. Đặt trong `src/tools` làm lớp tool sở hữu lượt và không còn mỏng theo D-011. Đặt trong `src/clients` trộn vòng lặp với Telegram và với SDK. Đặt ở root repo thì Worker không bundle.

## 3. Async

**Decision:** `run_turn` và phương thức `complete` của cổng là `async def`. Adapter dùng `AsyncAnthropic`.

**Rationale:** `execute_tool` đã là `async def`. Lượt phải `await` nó. Client đồng bộ trong hàm async sẽ chặn vòng sự kiện trên Worker. D-012 đã chọn async cho chỗ có gọi mạng hoặc kho, và test bằng `asyncio.run`.

**Alternatives considered:** Hàm sync bọc `asyncio.run` không chạy được khi Worker đã có vòng sự kiện. `pytest-asyncio` là dependency mới, bị cấm.

## 4. Ngân sách và chỗ không cắt được

**Decision:** Module lượt có `_now`. Hết giờ thì không bắt đầu lần gọi mô hình hoặc lần tool tiếp theo. Lần gọi mô hình đang chạy mở `async with AsyncAnthropic(..., timeout=phần giây còn lại, max_retries=0)`. Kết nối đóng khi hết khối. Lần `execute_tool` đã bắt đầu chạy đến khi trả về.

**Rationale:** Router đã chứng minh bịt `time.monotonic` làm gãy `asyncio` trên Windows. SDK nhận timeout theo từng client, và client được tạo cho từng lần gọi vì phần giây còn lại đổi. `execute_tool` không có timeout và không được sửa. `asyncio.wait_for` hủy task và biến ngân sách thành `CancelledError`, trái FR-011.

**Alternatives considered:** Sửa router để nhận timeout, bị cấm. Một client SDK dùng chung với timeout lúc đầu lượt sẽ không phản ánh phần giờ đã tiêu. Bắt `CancelledError` rồi đổi thành câu lỗi, bị cấm.

## 5. max_tokens và stop_reason

**Decision:** `max_tokens` là 2048. Chỉ `end_turn` trả văn bản. Chỉ `tool_use` với yêu cầu đủ id, tên, và object mới thành một vòng. Mọi `stop_reason` khác, gồm `max_tokens` khi một yêu cầu tool đang dở, không chạy tool và không gọi mô hình thêm.

**Rationale:** SDK bắt buộc `max_tokens`. 2048 là trần. Chỉ token sinh ra mới tính phí. `create_plan` tiếng Việt nhiều việc con có thể vượt 1024 và làm cả lượt ra câu lỗi. Spec không có thử lại, nên phản hồi bị cắt không được gửi tiếp.

**Alternatives considered:** 1024 để trần thấp hơn. Một kế hoạch tiếng Việt nhiều việc con có thể chạm trần đó. Bỏ `max_tokens` thì SDK không gửi được request. Coi `max_tokens` là `end_turn` và trả văn bản dở sẽ chạy một tool còn thiếu đối số. Gọi mô hình thêm sau `max_tokens` là thử lại, spec cấm.

## 6. Một hàm log

**Decision:** `run_turn` nhận một callable. Cùng object đó đi vào mọi `execute_tool`. Dòng tám khóa ghi khi `complete` trả về, trước tool của phản hồi đó. Hàm log ném `Exception` thì nuốt. Không nuốt `CancelledError`.

**Rationale:** Ràng buộc 6 đòi một luồng đúng thứ tự xảy ra. `execute_tool` tự ghi dòng bảy khóa bên trong, nên lượt không ghi hộ dòng tool và không đổi bảy khóa.

**Alternatives considered:** Hai hàm log cho hai loại dòng sẽ lệch thứ tự nếu người gọi ghép sai. Ghi dòng mô hình sau khi tool chạy xong đảo thứ tự xảy ra.

## 7. Khóa và dependency

**Decision:** Xóa dòng khai báo `ANTHROPIC_API_KEY` trong `settings.py`. Giữ `TELEGRAM_BOT_TOKEN`. Không thêm dependency. Không sửa `pyproject.toml`.

**Rationale:** Không còn chỗ Python nào đọc hằng đó. Lượt nhận khóa bằng đối số và không gọi `os.getenv`. `anthropic` đã nằm trong dependency chính, nên ràng buộc 12 không phải điểm dừng.

**Alternatives considered:** Giữ dòng `os.getenv` tạo một lối đọc môi trường mà FR-008 cấm. Tự thêm `anthropic` khi chưa có thì phải dừng; trường hợp đó không xảy ra. Viết adapter bằng `urllib` thay SDK là chọn cách khác, không được làm.

## 8. Lịch sử và khối tool

**Decision:** Lịch sử người gọi chỉ là `TextMessage`. Lượt không sửa list đó. Khối tool và kết quả tool chỉ đi vào `complete` kế tiếp của cùng lượt.

**Rationale:** Ràng buộc 10. Spec không có kho hội thoại. Trả cả khối tool ra ngoài sẽ thành trạng thái mà nguyên tắc II không cho giữ giữa các request.

**Alternatives considered:** Nối kết quả tool vào chính list lịch sử người gọi đưa sẽ sửa dữ liệu của người gọi và đưa khối tool ra ngoài lượt.

## 9. Test

**Decision:** Test lượt nhận một client giả cùng kiểu Protocol, trả danh sách phản hồi. Test adapter thay `AsyncAnthropic` bằng một lớp giả và đọc đối số constructor cùng đối số `messages.create`. Không đọc attribute của adapter.

**Rationale:** Ràng buộc 13 và 14. Năm luật có năm hàm test riêng. Bịt SDK ở test lượt sẽ kiểm nhầm tầng.

**Alternatives considered:** Một test lượt gọi adapter thật với mạng, trái FR-015. Đọc `_client` của adapter để biết khóa, trái ràng buộc 13.

## 10. Rủi ro chưa kiểm chứng

Timeout của httpx là giới hạn từng giai đoạn chứ không phải tổng thời gian. Chưa kiểm trên Worker, nơi fetch là fetch của JS, xem timeout có được tôn trọng không. Đo ở vòng route.
