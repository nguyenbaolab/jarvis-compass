# Contract: sendMessage

Client ở `src/clients/telegram.py`. Test bằng `httpx.MockTransport`. Không mở mạng.

## Request

`POST https://api.telegram.org/bot<token>/sendMessage`

JSON đúng hai khóa:

- `chat_id`: mã cuộc trò chuyện đã nhận.
- `text`: một phần đã tách, từ 1 đến 4096 đơn vị UTF-16.

Không có khóa `parse_mode`. Không có khóa nào khác. Dấu sao, gạch dưới, và backtick trong `text` đi nguyên.

Token nằm trong đường dẫn. Thông điệp lỗi và nhật ký không chứa token.

Timeout một phần: 10 giây.

## Kết quả

Gửi một phần thành công khi HTTP 2xx và JSON có `ok` là true.

Các trường hợp còn lại là gửi thất bại, gồm lỗi vận chuyển, HTTP không 2xx, và HTTP 200 với `ok` không phải true. Kênh không `mark_sent`. Câu đã lưu giữ nguyên. Người gọi webhook bị Hoãn.

Nhiều phần gửi theo thứ tự luật `split_utf16`. Ghép theo thứ tự ra đúng chuỗi gốc. Một phần giữa chừng thất bại thì dừng. Lần nhận sau gửi lại từ đầu cả chuỗi. Có thể làm phần đã tới xuất hiện lần nữa. Lát này chấp nhận gửi ít nhất một lần.

Câu trong ngữ cảnh là chuỗi gốc, không phải từng phần.

## Lỗi gửi vĩnh viễn

Lỗi vĩnh viễn, ví dụ chủ bot chặn bot, đi cùng nhánh gửi thất bại cho tới khi Telegram bỏ cuộc. Đã duyệt: mọi lỗi gửi là Hoãn. Không thêm nhánh dừng gửi.
