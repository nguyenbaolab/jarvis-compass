# Dòng ngày của một lượt

Hằng `SYSTEM_PROMPT` không chứa ngày. `run_turn` nhận `instant` có múi giờ, đọc một lần ở đầu lượt, và ghép một dòng sau hằng cho mọi lần gọi mô hình của lượt đó. Cùng mốc đó nằm trên `TurnContext` của lượt và là `moved_at` khi tool dời ngày ghi. Tool không đọc đồng hồ lần thứ hai.

Dòng do `turn_date_line` dựng từ `weekday_name_vi` và ngày Helsinki của mốc. Ba dòng nối bằng xuống dòng. Dòng 1:

`Hôm nay là thứ Sáu 06/11/2026 (2026-11-06), múi giờ Europe/Helsinki.`

Dòng 2 là `Tuần này: ` rồi bảy mục `{thứ} {ngày ISO}` từ thứ Hai đến Chủ nhật của tuần chứa hôm nay, nối bằng `, `, kết thúc bằng `.`. Với hôm nay 2026-11-06, tuần này là 2026-11-02 đến 2026-11-08. Dòng 3 là `Tuần sau: ` cùng dạng cho tuần kế tiếp, 2026-11-09 đến 2026-11-15. Chủ nhật 2026-11-08 vẫn thuộc tuần 2026-11-02 đến 2026-11-08.

Chủ nhật viết `Chủ nhật`, không viết `thứ Chủ nhật`. Ngày trong ngoặc là ngày ISO của cùng ngày Helsinki. Đoạn ngày của digest không có năm. Hai chỗ dùng chung `weekday_name_vi`, không dùng chung khuôn cả dòng.

Mốc không có múi giờ thì lỗi, không đoán UTC. Bộ v1 không có mốc từng ca. Lần chạy đó truyền `2026-11-06T08:00:00+02:00`. Bộ v2 truyền mốc ghi trong ca.

`from core.morning import helsinki_clock` vẫn dùng được. Hàm thật nằm ở `src/core/clock.py`.
