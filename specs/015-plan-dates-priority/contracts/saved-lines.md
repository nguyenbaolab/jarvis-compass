# Mẫu dòng bản ghép

Các chuỗi này chỉ ở `src/tools/saved_reply.py`. Bản ghép D-021 nối chúng khi lượt không kết thúc bình thường. Kết quả "trùng, chưa ghi" không dùng mẫu nào ở đây.

Sáu mẫu đang có giữ nguyên chữ:

- `Đã lưu kế hoạch {goal}.`
- `Đã lưu kế hoạch {goal} với việc {tiêu đề, ngăn bằng dấu phẩy}.`
- `Đã lưu việc {title} vào kế hoạch {goal}.`
- `Đã lưu việc {title} trong kế hoạch {goal} là {chưa làm|xong|bỏ qua}.`
- `Đã lưu ghi chú {note} cho việc {title} trong kế hoạch {goal}.`
- `Đã bỏ ghi chú của việc {title} trong kế hoạch {goal}.`

Dòng tạo kế hoạch không thêm ngày, sức, hay ưu tiên.

Năm mẫu mới:

- `Đã lưu ưu tiên {cao|vừa|thấp} cho kế hoạch {goal}.`
- `Đã bỏ ưu tiên của kế hoạch {goal}.`
- `Đã lưu sức {S|M|L} cho việc {title} trong kế hoạch {goal}.`
- `Đã bỏ sức của việc {title} trong kế hoạch {goal}.`
- `Đã lưu ngày của việc {title} trong kế hoạch {goal}.`

Mẫu ngày dùng cho lần ghi của `reschedule_subtasks` đã thành công, một dòng cho cả lần ghi. Nhiều việc thì nối tiêu đề bằng dấu phẩy, cùng kiểu dòng tạo kế hoạch. Không ghi ngày cũ và ngày mới vào mẫu. Lý do dời không vào mẫu.

Tổng là 11 mẫu. `docs/ARCHITECTURE.md` §2 đang nói sáu mẫu. Implement sửa câu đó. Bước plan không sửa file docs.
