# Contract: Webhook Telegram

Cập nhật 2026-11-05: dòng nhật ký của kênh có thêm khóa `reason`, `update_id`, `error_type` và `error_code`; xem docs/ARCHITECTURE.md §6. Đoạn nhật ký bên dưới giữ làm biên bản của spec 013, trừ câu về nội dung dòng kênh.

Route nhận update. Mã HTTP đã duyệt. Body của response rỗng ở mọi nhánh.

## Request

- `POST /telegram`.
- Header secret: `X-Telegram-Bot-Api-Secret-Token`.
- Cấu hình đọc từ `request.scope["env"]`, không đọc `os.environ` trong route.
- Ba tên: `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_ID`. Khóa mô hình: `ANTHROPIC_API_KEY`.

## Kết quả người gọi nhìn thấy

| Kết quả | Mã | Khi nào |
|---------|----|---------|
| Từ chối | 401 | Thiếu cấu hình secret, thiếu header, secret không khớp, hoặc thiếu token bot. |
| Hoãn | 503 | Lần nhận chồng khi lượt đang chạy. Gửi thất bại, câu giữ trong bản ghi. Kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho. Lượt đã xong nhưng lưu câu thất bại. Câu đã lưu nhưng ghi ngữ cảnh thất bại: không gửi, câu giữ nguyên, mô hình không bị gọi lại. |
| Bỏ qua | 200 | Không phải tin mới, không phải cuộc riêng, không phải chủ bot, thiếu danh tính chủ bot, hoặc body không phải update đọc được. |
| Xong | 200 | Đã gửi cả câu, hoặc lần nhận thấy update đã gửi xong. |

Từ chối và Hoãn khác mã. Bỏ qua và xong cùng 200. Telegram gửi lại khi không nhận 2xx.

Không ghi secret đúng, secret request đưa, token, chữ tin, câu trả lời, hay nội dung lỗi vào response hay vào nhật ký kênh. Dòng kênh có `outcome`, `reason`, thêm `update_id` khi là int, `error_type` khi bắt exception, và `error_code` khi có mã; không ghi message, hint, hay details, và không đổi bảy khóa tool hay tám khóa mô hình. Nhật ký lượt vẫn là bảy khóa tool và tám khóa mô hình, không thêm khóa.

## Thứ tự

Secret, rồi token, rồi loại update, rồi cuộc trò chuyện riêng, rồi danh tính chủ bot, rồi bản ghi update. Bước sau không chạy khi bước trước đã Từ chối hoặc Bỏ qua.

So secret bằng `hmac.compare_digest` trên hai `str`. Không cắt khoảng trắng. Không log hai chuỗi.

Mã người gửi là `int`, không phải `bool`. Khớp khi `str(mã)` bằng đúng chuỗi `TELEGRAM_OWNER_ID`. Không cắt khoảng trắng.

Tin chữ là `message.text` kiểu `str` còn chữ khác khoảng trắng. Chú thích ảnh không phải phần chữ chính. Chữ rỗng hoặc chỉ khoảng trắng, voice, ảnh, file, sticker, vị trí, danh thiếp, cuộc bình chọn: câu `Mình chỉ đọc được tin chữ.`, không gọi mô hình. Tin sửa, nút bấm, nhóm, siêu nhóm, kênh: Bỏ qua.

## Một update

`claim` một RPC. Lần chèn được hàng mới chạy lượt hoặc câu cố định của tin không phải chữ. Lần không chèn được hàng không chạy lượt thứ hai.

Lưu câu chỉ khi `reply` còn null. Lần thua không gửi câu của mình.

Đã có câu mà chưa gửi: gửi lại đúng nguyên văn, không chạy lượt. Đã gửi xong: không gửi thêm.
