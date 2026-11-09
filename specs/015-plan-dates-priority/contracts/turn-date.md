# Dòng ngày của một lượt

Hằng `SYSTEM_PROMPT` không chứa ngày. `run_turn` nhận `instant` có múi giờ, đọc một lần ở đầu lượt, và ghép một dòng sau hằng cho mọi lần gọi mô hình của lượt đó. Cùng mốc đó nằm trên `TurnContext` của lượt và là `moved_at` khi tool dời ngày ghi. Tool không đọc đồng hồ lần thứ hai.

Dòng do `turn_date_line` dựng từ `weekday_name_vi` và ngày Helsinki của mốc. Dạng:

`Hôm nay là thứ Sáu 06/11/2026, múi giờ Europe/Helsinki.`

Chủ nhật viết `Chủ nhật`, không viết `thứ Chủ nhật`. Có năm trên dòng này để mô hình ghi được ngày ISO. Đoạn ngày của digest không có năm. Hai chỗ dùng chung `weekday_name_vi`, không dùng chung khuôn cả dòng.

Mốc không có múi giờ thì lỗi, không đoán UTC. Bộ v1 không có mốc từng ca. Lần chạy đó truyền `2026-11-06T08:00:00+02:00`. Bộ v2 truyền mốc ghi trong ca.

`from core.morning import helsinki_clock` vẫn dùng được. Hàm thật nằm ở `src/core/clock.py`.
