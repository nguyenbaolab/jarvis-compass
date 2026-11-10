# Tool quét tải

Chín tool. `DEFINITIONS_VERSION` là 4. Không thêm tool. Sáu tool không nêu ở đây giữ schema bản 3.

Ba tool dưới nhận thêm khóa không bắt buộc. `additionalProperties` vẫn false.

## create_plan

Giữ `goal`, `priority`, `subtasks`.

Thêm:

- `confirm`: boolean. Mặc định false. True chỉ ở lượt sau, khi tool này đã báo ngày vượt và chủ bot vẫn muốn ghi.
- `load_moves`: mảng các object `{plan_id, subtask_id, scheduled_on}`. Cả ba khóa bắt buộc trong từng object. Vắng cả mảng thì không có danh sách. Đây là danh sách dời đã chốt, không phải việc của kế hoạch mới.

Mô tả tool nói thêm: ngày vượt thì chưa ghi; nói lại câu tool; chỉ đặt `confirm` true ở lượt sau.

## add_subtask

Giữ `plan_id`, `title`, `scheduled_on`, `effort`.

Thêm `confirm` và `load_moves` cùng kiểu với `create_plan`.

## reschedule_subtasks

Giữ `plan_id`, `changes`, `reason`, `confirm`.

`confirm` vẫn true chỉ ở lượt sau. Khi câu tool vừa báo vượt vừa báo trùng, một cờ đó bao cả hai.

Thêm `load_moves` cùng kiểu trên. `changes` vẫn là lần chủ bot đang xin. Không nhét việc của kế hoạch khác vào `changes`.

## Lượt

`execute_tool` đã nhận `turn`. `_create` và `_add` thôi bỏ `turn`. Hai handler truyền `turn`, `confirm` và `load_moves` khi khóa có trong input.

Không có `turn` mà lần ghi có ngày hôm nay hoặc ngày sau: tool lỗi, kho không đổi. Không ngày cần xét: `turn` trống vẫn được ghi.
