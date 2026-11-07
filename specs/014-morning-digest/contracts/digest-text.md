# Hợp đồng chữ bản tin và `/next`

Chữ, thứ tự đoạn, câu khi không có đoạn, và luật khớp `/next` nằm ở spec. File này chỉ chốt chỗ gọi.

## Hàm thuần

Đặt trong `src/core/morning.py`. Chỉ thư viện chuẩn, gồm `zoneinfo`. Không import `tzdata`, `fastapi`, `pydantic`, `tools`, `db`.

- `render_digest(plans) -> str`. Nhận tuple `Plan`. Tự sắp `created_order` tăng dần. Không gọi mạng, không đọc đồng hồ hệ thống.
- `is_next_command(text) -> bool`. `strip()` rồi `casefold()` bằng `"/next"`. Chỉ nhận `str`.
- `helsinki_clock(instant) -> (date, time)`. `instant` phải aware, quy về UTC trước khi đổi sang `Europe/Helsinki`.
- `digest_update_id(day) -> int`. Công thức ở [data-model.md](../data-model.md).
- `decide_digest(view) -> DigestDecision`. Ba giá trị: xong, gửi lại, dựng. Không nhận đồng hồ. Không có giá trị SaveUncertain.

`decide_receive` không đổi chữ ký và không đổi nhánh.

## `/next` trên đường update

`handle_update` gọi `is_next_command` sau nhánh tin không phải chữ và trước khi đọc lịch sử. Khớp thì:

1. `plans.list_newest_first()`. Lỗi: hoãn, reason store-unavailable đã có, không lưu câu, không gửi.
2. `render_digest` trên tuple vừa đọc.
3. `_save_context_send` với `remember=True` và reason trả lời thường.

Không gọi `run_turn`. Không đổi `write_channel_line`. Lần Telegram gửi lại lệnh này vẫn qua `decide_receive`.

`src/api/telegram_update.py` không import `clients`, `db`, `config`, `anthropic`.
