# Contract: Giới hạn mỗi lời gọi kho

Chỗ bảo đảm FR-001 nằm trong `src/tools`. `src/core` không chờ mạng và không đặt timeout. Trần HTTP nằm trong `src/db`. Trần đó không bảo đảm FR-001.

## Hàm số giây còn lại

`run_turn` truyền cho `execute_tool` một hàm không đối số, trả số giây còn lại: `lambda: _remaining(started)`. Không truyền một số tính sẵn. Không truyền mốc thời gian tuyệt đối.

Số tính trước `complete` đã cũ khi tool chạy. Tool đọc rồi ghi thì lời gọi sau phải thấy số đã giảm. `_now` trong `llm_turn` là đồng hồ duy nhất mà test bịt.

`execute_tool` có mặc định `None`, nghĩa là không giới hạn. Mặc định chỉ để test cũ. `run_turn` luôn truyền hàm.

## Trong tool

Đây là chỗ bảo đảm FR-001. Ngay trước mỗi lời gọi `add`, `get`, `list_newest_first`, hoặc `replace`, tool gọi hàm đó và chờ lời gọi bằng `asyncio.wait_for` với số vừa nhận.

Số còn lại nhỏ hơn hoặc bằng 0 trước khi một lời gọi kho bắt đầu: không gửi lời gọi. Tool trả `Không thực hiện được yêu cầu này.` Không đặt cờ hiệu lực ghi, vì chưa gửi gì. Lượt tự rơi vào lối hết giờ ở vòng kiểm kế tiếp.

Lời gọi đã gửi rồi quá hạn:

- Lời gọi đọc (`get`, `list_newest_first`) quá hạn: tool trả `Không thực hiện được yêu cầu này.` Không gọi lời ghi phía sau trong cùng tool.
- Lời gọi ghi (`add`, `replace`) quá hạn: tool trả `Chưa chắc thay đổi đã được lưu.`
- Lời gọi trả về trước hạn: kết quả thành công hoặc lỗi miền giữ như spec tool đó.

Kho giả không mở mạng. Một ca để kho giả không trả lời và thấy tool bị bỏ trong hạn. Một ca đi qua `run_turn` với kho giả không trả lời, chứng minh lượt trả trong hạn. Cả hai không cần Supabase.

## Trong db

`postgrest_client` tạo `httpx.AsyncClient` với mức trần cố định 20 giây. Hằng nằm riêng trong `src/db`, ghi chú là bằng ngân sách của lượt. Client này truyền vào `AsyncPostgrestClient` bằng `http_client`. Không dùng đối số `timeout=` đã deprecated. Không thêm gói. Không driver TCP.

Cổng `PlanStore` giữ nguyên nên số còn lại không tới được `SupabasePlanStore`. Timeout của httpx tính theo từng pha (connect, read, write, pool), không phải tổng thời gian lời gọi. Mức trần chỉ để giải phóng kết nối. Nó không bảo đảm FR-001.

Lỗi mạng của httpx không phải quá hạn (ví dụ kết nối bị ngắt) không có xử lý riêng ở lát này. Nó vẫn đi qua except Exception của router thành "Không thực hiện được yêu cầu này." như hiện nay. Với lần ghi, câu đó có thể sai nếu kho đã nhận lệnh. Đây là giới hạn đã biết, chưa thuộc lát nào.

## Worker

Hành vi timeout trên Pyodide là chưa kiểm chứng. Pytest trên CPython không đổi nhãn đó. Cách nhìn trên Worker nằm ở [quickstart.md](../quickstart.md).
