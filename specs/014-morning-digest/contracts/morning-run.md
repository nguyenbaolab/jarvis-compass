# Hợp đồng lần chạy sáng

## Lịch

`wrangler.jsonc` khai ba cron UTC: `0 5 * * *`, `0 6 * * *`, `0 7 * * *`.

`src/entry.py` là file duy nhất import `workers`. `scheduled` gọi một hàm: `run_morning(env)` trong `src/scheduler/morning.py`. Hàm này được phép import `config`, `db`, `clients`, `core`. Không import `workers`. Không import `anthropic`. Không gọi `run_turn` hay `execute_tool`.

## Cổng giờ

Đồng hồ sản xuất là UTC hiện tại, đổi bằng `helsinki_clock`. Test tiêm `datetime` aware.

Giờ địa phương nhỏ hơn 08:00: outcome `before_eight`, không `claim`, không gửi, không `mark`. Từ 08:00:00 trở đi thì vào máy trạng thái ở [data-model.md](../data-model.md).

`chat_id` lấy từ `require_telegram_owner_id` theo luật ở research mục 5. Không đạt: `deferred`, không gửi.

Đọc kế hoạch lỗi: không dựng chữ, không gọi mô hình, không `mark`, outcome `deferred`.

## Gửi

Tách bằng `split_utf16` của spec 013. Người gửi chỉ gửi từng phần, không tự tách. Ngữ cảnh lưu một chuỗi, vai `assistant`, trước lần gửi. Lỗi ghi ngữ cảnh: không gửi, không `mark`.

`mark` không ném lỗi mới được outcome `sent` hoặc `resend`. `mark` ném lỗi sau khi gửi: outcome `deferred`, `sent_at` vẫn null. Chi tiết ở research mục 6.

## Dòng log

Đúng một dòng mỗi lần `run_morning` được gọi. Bảy khóa, luôn có, thứ tự và giá trị ở research mục 7. Năm outcome: `before_eight`, `already_sent`, `sent`, `resend`, `deferred`. Nghĩa từng giá trị ở research mục 7. Không chứa nội dung tin. Không ghi thêm dòng kênh, dòng tool, hay dòng mô hình cho lần cron.

`/next` không ghi dòng này và không đổi dấu ngày.
