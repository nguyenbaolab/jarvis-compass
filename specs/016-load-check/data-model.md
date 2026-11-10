# Data model: Quét tải

Không bảng mới. Không cột mới. Không đổi trường của `Plan` hay `Subtask`. Các khối dưới đây chỉ sống trong một lần gọi tool.

## Đã có và được đọc

- `Plan.priority`, `Plan.created_order`, `Plan.version`, `Plan.goal`, `Plan.id`
- `Subtask.scheduled_on`, `Subtask.effort`, `Subtask.status`, thứ tự trong `Plan.subtasks`, `Subtask.title`, `Subtask.id`
- `EFFORT_HOURS`: S = 1, M = 3, L = 6
- Dòng `subtask_date_moves` chỉ sinh khi một việc đổi từ một ngày sang một ngày khác qua `replace_plan`. Lần gọi đầu thấy vượt không sinh dòng. Việc ở lại ngày gốc không sinh dòng.

## Quỹ

`day_budget(day) -> int`

Mọi ngày lịch, gồm ngày đã qua và hôm nay, trả 8. Không đọc kho. Không gọi routine.

## Tải một ngày

Đầu vào là mọi `Plan` của một lần `list_plans`, một ngày, và `today`.

- Ngày trước `today`: tổng 0, số việc tính tạm 0.
- Hôm nay và ngày sau: cộng `task_hours` của mọi việc chưa làm có `scheduled_on` đúng ngày đó, mọi kế hoạch.
- Việc chưa làm không sức cộng 3 và tăng số việc tính tạm.
- Việc đã xong, việc bỏ qua, và việc không mang ngày đó cộng 0.

Vượt khi tổng lớn hơn `day_budget`. Tổng bằng 8 chưa vượt.

## Việc dời

Một phần tử danh sách có `plan_id`, `subtask_id`, tiêu đề, tên kế hoạch, và ngày đích.

Ứng viên là việc chưa làm đã có trên ngày vượt từ trước lần ghi. Việc lần ghi này vừa đặt không phải ứng viên và vẫn nằm trong tổng.

Thứ tự: thấp, rồi trống cùng vừa, rồi cao. Trống và vừa là một mức khi so. Giá trị ưu tiên đã lưu không đổi. Cùng mức: hạn kế hoạch muộn hơn trước. Hạn là ngày muộn nhất của việc chưa làm có ngày. Cùng hạn: `created_order` nhỏ hơn đứng trước. Cùng kế hoạch: việc đứng sau trong `subtasks` đứng trước. Số giờ không đổi thứ tự.

Đoạn đề xuất là đoạn đầu ngắn nhất sao cho tổng còn lại không còn lớn hơn quỹ. Không tách giờ của một việc.

Ngày đích là ngày gần nhất trong bảy ngày lịch ngay sau ngày vượt mà còn đủ quỹ. Đủ quỹ gồm giờ chưa làm đã có, giờ các việc đề xuất trước đã nhận ngày đó, và giờ việc đang gán. Hết bảy ngày thì việc không vào danh sách và giữ ngày gốc. Không tìm ngày thứ tám. Thứ Bảy và Chủ nhật vẫn tính.

`load_moves` trên tool là danh sách chủ bot đã chốt. Code ghi đúng mảng đó, không thêm phần tử. Ngày đích trong phần tử được ghi dù khác ngày code đã đề xuất.

## Ghi nhiều lần cùng một kế hoạch

Các lần ghi của cùng một kế hoạch trong một lần gọi tool nối tiếp nhau trên bản đã áp lần trước. Lần xin của chủ bot đi trước, rồi các phần tử `load_moves` theo thứ tự mảng. Mỗi lần ghi sau thấy các việc và ngày mà lần ghi trước đã đặt.

## Không lưu

Cảnh báo vượt không có bảng. Không có cột quỹ. Không có cờ xác nhận trong kho. `turn.clash_reported` mất khi lần `run_turn` trả về.
