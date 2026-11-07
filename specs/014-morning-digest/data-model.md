# Data model: Bản tin sáng

Không bảng mới. Không cột mới. Không đổi `Plan`, `Subtask`, hay `PlanStore` (D-011).

## Dòng ngày digest

Một dòng trong `telegram_updates` cho một ngày lịch Helsinki.

| Cột | Giá trị |
| --- | --- |
| `update_id` | `-(năm * 10000 + tháng * 100 + ngày)`, ví dụ `-20261107` |
| `started_at` | mốc UTC của lần `claim` đầu |
| `reply` | null cho đến khi dựng xong; sau đó là cả chuỗi sẽ gửi |
| `sent_at` | null cho đến khi `mark_telegram_sent` đổi được một dòng |

Mã âm không đụng mã update dương của Telegram. Không có `CHECK` dương trên cột này. Một ngày một dòng vì `update_id` là khóa chính.

Trạng thái, đọc từ dòng sau `claim`:

| `sent_at` | `reply` | Việc lần chạy này làm |
| --- | --- | --- |
| có | có | dừng |
| null | có | gửi lại đúng `reply`, không dựng lại |
| null | null | dựng, lưu, gửi |

Trước 08:00 Helsinki không tạo dòng.

## Dòng ngữ cảnh

Một dòng `telegram_context_messages` cho ngày đó.

| Cột | Giá trị |
| --- | --- |
| `update_id` | cùng mã âm |
| `role` | `assistant` |
| `chat_id` | số nguyên của `TELEGRAM_OWNER_ID` |
| `body` | đúng chuỗi `reply` |
| `saved_at` | mốc UTC lúc ghi |

Không có dòng `role = user` cho digest. Khóa `(update_id, role)` nên lần thử lại không thêm dòng assistant thứ hai. Lượt mô hình sau đọc theo `chat_id` và `saved_at`, nên dòng này nằm trong cửa sổ ngữ cảnh hiện có.

`/next` không dùng mã âm. Update thật của lệnh đó có hai dòng ngữ cảnh, `user` rồi `assistant`, do đường update thường ghi. Lệnh này không ghi `sent_at` của ngày digest và không xóa nó.

## Chữ dựng từ kế hoạch

Đọc mọi `Plan` đang lưu. Kế hoạch còn trong kho là kế hoạch active. Không thêm cờ đóng.

Mỗi đoạn lấy `goal` và tiêu đề của việc con `pending` đầu tiên theo thứ tự đã lưu. Việc `done` và `skipped` bị bỏ qua. Kế hoạch không còn việc `pending` không có đoạn. Các đoạn xếp theo `created_order` tăng dần. `list_newest_first` không đổi hướng.

Không đổi field nào của `Plan` hay `Subtask`. Ghi chú không vào tin. Ngày tháng không vào tin.

## Những thứ không thêm

- Không bảng ngày digest.
- Không cột "đã gửi sáng" trên một bảng khác. `sent_at` của dòng mã âm là dấu đã xác nhận.
- Không RPC mới và không đổi chữ ký RPC cũ.
