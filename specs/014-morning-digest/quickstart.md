# Quickstart: kiểm bản tin sáng

Bước plan không chạy các lệnh dưới đây. Implement chạy pytest. Deploy và bắn cron là việc Starter tự làm sau, không nằm trong implement.

## Pytest

Từ gốc repo:

```text
uv run pytest
```

`.\scripts\check.ps1 -AllowList specs/014-morning-digest/allowed-files.txt` chỉ chạy sau khi `/speckit-tasks` đã tạo allow-list. Chưa tạo file đó ở bước plan.

Các ca cần có, đồ giả, không mạng:

- Chữ: kế hoạch cũ đứng trước; kế hoạch không còn `pending` mất đoạn; không đoạn nào thì đúng câu spec; `/Next` và ` /next ` khớp; `/next@bot` không khớp.
- Sáu mốc UTC ra độ lệch giờ Helsinki 2, 3, 2, 3, 3, 2: `2026-01-15T12:00Z`, `2026-07-15T12:00Z`, `2026-03-29T00:59Z`, `2026-03-29T01:00Z`, `2026-10-25T00:59Z`, `2026-10-25T01:00Z`.
- 07:59 Helsinki không claim. 08:00 claim và được phép gửi.
- `decide_digest`: `reply` null sau hơn 90 giây thì dựng lại. `decide_receive` với cùng tuổi đó vẫn SaveUncertain và vẫn dùng câu chưa chắc. Hàm cũ không đổi.
- Digest: một dòng ngữ cảnh `assistant`, không dòng `user`. Lần sau khi đã có `reply` gửi đúng chữ đó và `append` không thêm dòng. Gửi lỗi thì `sent_at` vẫn null. `mark` không ném lỗi mới thành `sent` hoặc `resend`; `mark` ném lỗi thì `deferred`.
- Dòng log sáng có đúng bảy khóa và không chứa tiêu đề kế hoạch.
- `/next`: không gọi `run_turn`, vẫn hai dòng ngữ cảnh, một dòng log kênh khóa cũ, không dòng log mô hình.
- Đọc kế hoạch lỗi: digest không mark; `/next` hoãn và không gửi câu chưa chắc.

`tests/test_rpc_returns.py` và các test log tool / log mô hình phải xanh mà không sửa kỳ vọng của chúng.

## Ép một lần cron

Không chờ 08:00. Không thêm route đo đồng hồ. Không thêm biến để tắt cổng giờ.

Trên `uv run pywrangler dev`, ứng viên là:

```text
GET /__scheduled?cron=0+5+*+*+*
```

Đối chiếu đường dẫn với bản `pywrangler` đang cài và với tài liệu Cron Triggers trước khi gọi. Đọc một dòng JSON `event` bằng `morning_digest`.

Trên Worker đã deploy, bắn lịch `0 5 * * *` từ dashboard hoặc từ API trigger của tài liệu lúc kiểm. Mùa đông kỳ vọng `local_time` là `07:00` và `outcome` là `before_eight`, không có tin mới. `0 6 * * *` mới là lần được phép gửi. Mùa hè thì `0 5 * * *` đã là 08:00 địa phương.

`spike/cron-checkin` và `spike/zoneinfo-pyodide` không được merge nguyên trạng. Route `/spike/tz` và cron năm phút không đi vào nhánh này.
