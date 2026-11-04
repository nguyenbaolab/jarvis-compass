# Quickstart: kiểm kênh Telegram trên máy

Không gọi Telegram thật, không deploy, không `pywrangler dev`, không `db push`, không `setWebhook`.

## Luật không cần kho

Từ gốc repo:

```text
uv run pytest tests/test_telegram_split.py tests/test_telegram_context_window.py tests/test_telegram_receive.py tests/test_telegram_update_flow.py tests/test_telegram_client.py tests/test_telegram_route.py tests/test_settings_telegram.py tests/test_llm_turn.py tests/test_app_loads_plan_store.py
```

`tests/test_eval_*` chạy cùng bộ pytest thường, không sửa file eval.

Kỳ vọng ngắn:

- 4096 đơn vị UTF-16 thành một phần. 2049 emoji ngoài mặt phẳng cơ bản thành hai phần. Ghép lại đúng chuỗi. Không phần rỗng.
- Đúng 20 tin và đúng 24 giờ còn trong ngữ cảnh. Tin thứ 21 và tin cũ hơn 24 giờ không vào.
- Hai lần nhận chồng: một lượt. Lưu câu thua thì lần thua không gửi.
- Lưu câu ném lỗi: 0 lần gửi, Hoãn, một kế hoạch. Lần sau, đồng hồ đẩy qua khoảng lượt đã chết, gửi `Chưa chắc tin này đã được xử lý.` một lần.
- Ghi ngữ cảnh ném lỗi ở lượt mới: 0 lần gửi, Hoãn, một lượt, câu giữ nguyên. Lần nhận sau ghi đủ hai vai một lần rồi gửi đúng câu đã lưu. Gửi lại khi ngữ cảnh đã có thì không nhân đôi.
- Đúng 90 giây vẫn Hoãn. Qua 90 giây thì câu chưa chắc. Dưới 90 giây vẫn Hoãn. Không ngủ thật.
- MockTransport thấy JSON chỉ có `chat_id` và `text`.
- App vẫn nạp `db.plan_store` khi không có env Telegram.

Ba assert cũ trong `tests/test_llm_turn.py` đổi như plan. Các assert khác của file đó giữ nguyên.

## Contract trên Supabase local

Cùng cách với contract kế hoạch. Ghim CLI `npx --yes supabase@2.122.0`. `start` rồi `db reset` sau khi implement đã có file migration. Đọc `status -o json`, đặt `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` trong tiến trình pytest. Host là `127.0.0.1` hoặc `localhost`.

```text
uv run pytest tests/test_telegram_channel_contract.py
```

Thiếu biến hoặc không nối được thì skip đúng helper local hiện có. Host không phải local thì fail trước khi gọi mạng. Test xóa dòng nó tạo, không xóa trong `src/`.

`.\scripts\check.ps1` dùng `--fail-on-skip`. Phiên kiểm cần kho local đang chạy nếu file contract nằm trong lần chạy đó.

## Chưa làm ở vòng này

Đăng ký webhook, Workers Paid, đo bộ nhớ, `pywrangler dev`, migration lên cloud, deploy.
